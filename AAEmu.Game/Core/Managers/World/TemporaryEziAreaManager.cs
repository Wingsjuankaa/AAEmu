using System.Numerics;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Slaves;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Core.Managers.World;

/// <summary>GM-created, fixed-position harbor areas. No changes to retail geometry or saved spawns.</summary>
public sealed class TemporaryEziAreaManager
{
    public const uint EziBuffId = 13816;
    public const uint MooredBuffId = 13817;
    public const int MaxSeconds = 86400;
    public const float DefaultRadius = 50;
    private static readonly uint[] BuffIds = [EziBuffId, MooredBuffId];
    private readonly object _lock = new();
    private readonly Dictionary<uint, Area> _areas = [];
    private readonly Dictionary<(Slave Hull, uint BuffId), Buff> _ownedBuffs = [];
    private sealed record Area(Vector3 Position, float Radius, DateTime Expires);

    public void Place(uint creatorId, Vector3 position, int seconds, float radius, DateTime now)
    {
        if (seconds is < 1 or > MaxSeconds)
            throw new ArgumentOutOfRangeException(nameof(seconds));
        if (!float.IsFinite(radius) || radius is < 5 or > 500)
            throw new ArgumentOutOfRangeException(nameof(radius));
        if (!float.IsFinite(position.X) || !float.IsFinite(position.Y) || !float.IsFinite(position.Z))
            throw new ArgumentOutOfRangeException(nameof(position));
        lock (_lock)
            _areas[creatorId] = new Area(position, radius, now.AddSeconds(seconds));
    }

    public bool Remove(uint creatorId)
    {
        lock (_lock)
            return _areas.Remove(creatorId);
    }

    public void Tick(WorldInstance world)
    {
        lock (_lock)
        {
            if (_areas.Count == 0 && _ownedBuffs.Count == 0)
                return;
        }
        Reconcile(DateTime.UtcNow, world.GetAllSlaves(), SkillManager.Instance.GetBuffTemplate,
            (hull, buffId) => HasNaturalSource(world, hull, buffId));
    }

    private static bool HasNaturalSource(WorldInstance world, Slave hull, uint buffId)
    {
        // Match the existing harbor consumer, which routes an owner's SphereBuff to their hull.
        var owner = hull.Summoner;
        if (owner?.ParentWorld != world)
            return false;
        foreach (var geo in world.SphereQuestManager.GetContainingQuestAreaSpheres(
                     owner.Transform.ZoneId, owner.Transform.World.Position))
        {
            var sphere = geo.DbSphere;
            if (sphere?.SphereDetailType == "SphereBuff" &&
                SphereGameData.Instance.GetSphereBuff(sphere.SphereDetailId)?.BuffId == buffId &&
                UnitRequirementsGameData.Instance.CanTriggerSphere(sphere, owner))
                return true;
        }
        return false;
    }

    internal void Reconcile(DateTime now, IReadOnlyList<Slave> hulls,
        Func<uint, BuffTemplate> templateFor, Func<Slave, uint, bool> hasNaturalSource)
    {
        lock (_lock)
        {
            foreach (var id in _areas.Where(x => x.Value.Expires <= now).Select(x => x.Key).ToArray())
                _areas.Remove(id);
            var covered = new HashSet<Slave>();
            foreach (var hull in hulls)
            {
                if (hull?.Template?.IsZoneSimulatedHull() != true || hull.Hp <= 0)
                    continue;
                var position = hull.Transform.World.Position;
                if (!_areas.Values.Any(a => Vector3.DistanceSquared(a.Position, position) <= a.Radius * a.Radius))
                    continue;
                covered.Add(hull);
                foreach (var buffId in BuffIds)
                {
                    if (hull.Buffs.CheckBuff(buffId))
                        continue;
                    var template = templateFor(buffId);
                    if (template == null)
                        continue;
                    var buff = new Buff(hull, hull, new SkillCasterUnit(hull.ObjId), template, null, now);
                    var oldHp = hull.Hp;
                    var oldMaxHp = hull.MaxHp;
                    hull.Buffs.AddBuff(buff);
                    // Only own the exact effect we installed; immunity or a concurrent source may win.
                    if (ReferenceEquals(hull.Buffs.GetEffectFromBuffId(buffId), buff))
                        _ownedBuffs[(hull, buffId)] = buff;
                    RefreshHealth(hull, oldHp, oldMaxHp);
                }
            }
            foreach (var (key, buff) in _ownedBuffs.ToArray())
            {
                var current = key.Hull.Buffs.GetEffectFromBuffId(key.BuffId);
                if (!ReferenceEquals(current, buff))
                {
                    _ownedBuffs.Remove(key);
                    continue;
                }
                // A real harbor now supplies this effect. Relinquish it without stripping it.
                if (hasNaturalSource(key.Hull, key.BuffId))
                {
                    _ownedBuffs.Remove(key);
                    continue;
                }
                if (covered.Contains(key.Hull))
                    continue;
                var oldHp = key.Hull.Hp;
                var oldMaxHp = key.Hull.MaxHp;
                key.Hull.Buffs.RemoveEffect(buff.Index, notifyZone: true);
                RefreshHealth(key.Hull, oldHp, oldMaxHp);
                _ownedBuffs.Remove(key);
            }
        }
    }

    public void Clear()
    {
        lock (_lock)
        {
            _areas.Clear();
            Reconcile(DateTime.UtcNow, [], _ => null, (_, _) => false);
        }
    }

    private static void RefreshHealth(Slave hull, int oldHp, int oldMaxHp)
    {
        hull.Hp = SlaveHealthCapRules.AfterMaxHpChanged(oldHp, oldMaxHp, hull.MaxHp);
        if (hull.Hp == oldHp)
            return;
        hull.BroadcastPacket(new SCUnitPointsPacket(hull.ObjId, hull.Hp, hull.Mp), false);
        hull.ParentWorld?.SlaveManager?.UpdateSlaveRepairPoints(hull);
    }
}
