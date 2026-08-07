using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Skills.Utils;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;

using NLog;

namespace AAEmu.Game.Models.Game.World
{
    public enum AreaShapeType
    {
        Sphere = 1,
        Cuboid = 2,
        ForwardCuboid = 3
    }
    public class AreaShape
    {
        public uint Id { get; set; }
        public AreaShapeType Type { get; set; }
        public float Value1 { get; set; }
        public float Value2 { get; set; }
        public float Value3 { get; set; }

        public List<T> ComputeCuboid<T>(GameObject origin, List<T> toCheck) where T : GameObject
        {
            // Z check
            var zOffset = Value3;
            toCheck = toCheck.Where(o => o.Transform.World.Position.Z >= origin.Transform.World.Position.Z - zOffset && o.Transform.World.Position.Z <= origin.Transform.World.Position.Z + zOffset).ToList();
            if (toCheck.Count == 0)
                return toCheck;

            // Triangle check
            var vertices = MathUtil.GetCuboidVertices(Value1, Value2,
                origin.Transform.World.Position.X, origin.Transform.World.Position.Y,
                //origin.Transform.World.ToRollPitchYawSBytes().Item3);
                origin.Transform.World.Rotation.Z);

            toCheck = toCheck.Where(o =>
            {
                var tri1 = MathUtil.PointInTriangle((o.Transform.World.Position.X, o.Transform.World.Position.Y), vertices[0], vertices[1],
                    vertices[2]);

                var tri2 = MathUtil.PointInTriangle((o.Transform.World.Position.X, o.Transform.World.Position.Y), vertices[1], vertices[2],
                    vertices[3]);

                return tri1 || tri2;
            }).ToList();

            return toCheck;
        }

        /// <summary>
        /// AA8 kind 3 is a forward-oriented prism: value1 is the half-width,
        /// value2 is the distance in front of the source, and value3 is the
        /// vertical half-height. Unlike kind 2, it does not extend behind the
        /// source. Native rows use it for path attacks such as 2 x 30 m shots
        /// and 2 x 7 m charges.
        /// </summary>
        public List<T> ComputeForwardCuboid<T>(GameObject origin, List<T> toCheck) where T : GameObject
        {
            var position = origin.Transform.World.Position;
            var yaw = origin.Transform.World.Rotation.Z;
            var forwardX = -MathF.Sin(yaw);
            var forwardY = MathF.Cos(yaw);
            var rightX = MathF.Cos(yaw);
            var rightY = MathF.Sin(yaw);

            return toCheck.Where(candidate =>
            {
                var candidatePosition = candidate.Transform.World.Position;
                var deltaX = candidatePosition.X - position.X;
                var deltaY = candidatePosition.Y - position.Y;
                var forwardDistance = deltaX * forwardX + deltaY * forwardY;
                var rightDistance = deltaX * rightX + deltaY * rightY;
                var verticalDistance = MathF.Abs(candidatePosition.Z - position.Z);

                return forwardDistance >= 0f && forwardDistance <= Value2 &&
                       MathF.Abs(rightDistance) <= Value1 &&
                       verticalDistance <= Value3;
            }).ToList();
        }
    }

    public class AreaTrigger
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();
        public AreaShape Shape { get; set; }
        public Doodad Owner { get; set; }
        public Unit Caster { get; set; }
        private List<Unit> Units { get; set; }


        public uint SkillId { get; set; }
        public ushort TlId { get; set; }
        public Skill OriginSkill { get; set; }
        public SkillTargetRelation TargetRelation { get; set; }
        public uint TargetBuffTagId { get; set; }
        public uint TargetNoBuffTagId { get; set; }
        public BuffTemplate InsideBuffTemplate { get; set; }
        public List<EffectTemplate> EffectPerTick { get; set; }
        public int TickRate { get; set; }
        private DateTime _lastTick = DateTime.MinValue;

        public AreaTrigger()
        {
            Units = new List<Unit>();
        }

        public static Skill SelectOriginSkill(bool useOriginSource, Skill originSkill)
        {
            return useOriginSource ? originSkill : null;
        }

        public CastAction CreateCastAction(Buff activeBuff = null)
        {
            return activeBuff != null
                ? (CastAction)new CastBuff(activeBuff)
                : new CastSkill(SkillId, TlId);
        }

        public EffectSource CreateEffectSource()
        {
            return new EffectSource(OriginSkill);
        }

        public void UpdateUnits()
        {
            if (Owner == null || !Owner.IsVisible)
            {
                AreaTriggerManager.Instance.RemoveAreaTrigger(this);
                return;
            }

            var units = WorldManager.Instance.GetAroundByShape<Unit>(Owner, Shape);

            var leftUnits = Units.Where(u => units.All(u2 => u.ObjId != u2.ObjId));
            var newUnits = units.Where(u => Units.All(u2 => u.ObjId != u2.ObjId));

            foreach (var newUnit in newUnits)
            {
                OnEnter(newUnit);
            }

            foreach (var leftUnit in leftUnits)
            {
                OnLeave(leftUnit);
            }

            Units = units;
        }

        public void OnEnter(Unit unit)
        {
            if (Caster == null)
                return;

            if (SkillTargetingUtil.IsRelationValid(TargetRelation, Caster, unit) && MeetsBuffTagRequirements(unit))
                InsideBuffTemplate?.Apply(
                    Caster,
                    new SkillCasterUnit(Caster.ObjId),
                    unit,
                    new SkillCastUnitTarget(unit.ObjId),
                    CreateCastAction(),
                    CreateEffectSource(),
                    null,
                    DateTime.UtcNow);
            // unit.Effects.AddEffect(new Effect(Owner, Caster, new SkillCasterUnit(Caster.ObjId), InsideBuffTemplate, null, DateTime.UtcNow));
        }

        public bool MeetsBuffTagRequirements(Unit unit)
        {
            if (unit == null)
                return false;
            return PassesBuffTagFilter(
                TargetBuffTagId,
                TargetBuffTagId != 0 && unit.Buffs.CheckBuffTag(TargetBuffTagId),
                TargetNoBuffTagId,
                TargetNoBuffTagId != 0 && unit.Buffs.CheckBuffTag(TargetNoBuffTagId));
        }

        public static bool PassesBuffTagFilter(
            uint requiredTagId,
            bool hasRequiredTag,
            uint excludedTagId,
            bool hasExcludedTag)
        {
            return (requiredTagId == 0 || hasRequiredTag) &&
                   (excludedTagId == 0 || !hasExcludedTag);
        }

        public void OnLeave(Unit unit)
        {
            if (InsideBuffTemplate != null)
                unit.Buffs.RemoveBuff(InsideBuffTemplate.BuffId);
        }

        public void OnDelete()
        {
            if (InsideBuffTemplate != null)
            {
                foreach (var unit in Units)
                {
                    unit.Buffs.RemoveBuff(InsideBuffTemplate.BuffId);
                }
            }
        }

        public void ApplyEffects()
        {
            if (InsideBuffTemplate == null)
                return;
            if (Caster == null)
                return;

            var unitsToApply = SkillTargetingUtil.FilterWithRelation(TargetRelation, Caster, Units)
                .Where(MeetsBuffTagRequirements);
            foreach (var unit in unitsToApply)
            {
                foreach (var effect in EffectPerTick)
                {
                    if (effect is BuffEffect buffEffect && unit.Buffs.CheckBuff(buffEffect.BuffId))
                        continue;
                    var eff = unit.Buffs.GetEffectFromBuffId(InsideBuffTemplate.BuffId);
                    var castAction = CreateCastAction(eff);

                    effect.Apply(
                        Caster,
                        new SkillCasterUnit(Caster.ObjId),
                        unit,
                        new SkillCastUnitTarget(unit.ObjId),
                        castAction,
                        CreateEffectSource(),
                        new SkillObject(),
                        DateTime.UtcNow);
                }
            }
        }

        // Called every 50ms
        public void Tick(TimeSpan delta)
        {
            UpdateUnits();
            if (TickRate > 0)
                if ((DateTime.UtcNow - _lastTick).TotalMilliseconds > TickRate)
                {
                    ApplyEffects();
                    _lastTick = DateTime.UtcNow;
                }
        }
    }
}
