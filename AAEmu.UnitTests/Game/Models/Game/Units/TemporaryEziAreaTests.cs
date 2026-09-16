using System.Numerics;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Slaves;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;


namespace AAEmu.UnitTests.Game.Models.Game.Units;

public class TemporaryEziAreaTests
{
    private static readonly DateTime Now = new(2026, 9, 16, 15, 0, 0, DateTimeKind.Utc);
    private sealed class Hull : Slave
    {
        public override int MaxHp => 100;
    }
    private sealed class Rig
    {
        public Hull Hull { get; } = new() { ObjId = 10, Hp = 100,
            Template = new SlaveTemplate { SlaveKind = SlaveKind.Fishboat } };
        public Dictionary<uint, Buff> Effects { get; } = [];
        public List<uint> Removals { get; } = [];
        private uint _index;
        public Rig()
        {
            var buffs = Mock.Of<IBuffs>();
            Hull.Buffs = buffs.Object;
            buffs.CheckBuff(Any<uint>()).Returns((uint id) => Effects.ContainsKey(id));
            buffs.GetEffectFromBuffId(Any<uint>()).Returns((uint id) => Effects.GetValueOrDefault(id));
            buffs.AddBuff(Any<Buff>(), 0, 0).Callback((Buff buff, uint index, int duration) =>
            {
                buff.Index = ++_index;
                Effects[buff.Template.Id] = buff;
            });
            buffs.RemoveEffect(Any<uint>(), true).Callback((uint index, bool notifyZone) =>
            {
                var id = Effects.Single(x => x.Value.Index == index).Key;
                Effects.Remove(id);
                Removals.Add(id);
            });
        }
        public void Move(float x) => Hull.Transform.Local.SetPosition(x, 0, 0, 0, 0, 0);
        public void Tick(TemporaryEziAreaManager manager, DateTime now, bool natural = false) =>
            manager.Reconcile(now, [Hull], id => new BuffTemplate { Id = id }, (_, _) => natural);
    }

    [Test]
    public async Task FixedAreaAppliesToEnteringHullAndRemovesBothEffectsAtDeadline()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        manager.Place(1, Vector3.Zero, 20, 50, Now);
        rig.Move(51);
        rig.Tick(manager, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
        rig.Move(50);
        rig.Tick(manager, Now.AddSeconds(19));
        await Assert.That(rig.Effects.Keys.Order().ToArray()).IsEquivalentTo(new uint[] { 13816, 13817 });
        var effects = rig.Effects.Values.ToArray();
        rig.Tick(manager, Now.AddSeconds(19.5));
        await Assert.That(effects.All(e => ReferenceEquals(rig.Effects[e.Template.Id], e))).IsTrue();
        rig.Tick(manager, Now.AddSeconds(20));
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
        await Assert.That(rig.Removals.Count).IsEqualTo(2);
    }

    [Test]
    public async Task OverlapRetainsEffectsUntilLastAreaExpiresAndExitRemovesImmediately()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        manager.Place(1, Vector3.Zero, 2, 50, Now);
        manager.Place(2, Vector3.Zero, 5, 50, Now);
        rig.Tick(manager, Now);
        rig.Tick(manager, Now.AddSeconds(2));
        await Assert.That(rig.Effects.Count).IsEqualTo(2);
        rig.Move(51);
        rig.Tick(manager, Now.AddSeconds(3));
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
        rig.Move(0);
        rig.Tick(manager, Now.AddSeconds(4));
        await Assert.That(rig.Effects.Count).IsEqualTo(2);
        rig.Tick(manager, Now.AddSeconds(5));
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
    }

    [Test]
    public async Task ReplacingAreaMovesItsCenterAndCancelOnlyRemovesCreatorsArea()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        manager.Place(1, Vector3.Zero, 20, 50, Now);
        rig.Tick(manager, Now);
        manager.Place(1, new Vector3(200, 0, 0), 20, 50, Now);
        rig.Tick(manager, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
        rig.Move(200);
        rig.Tick(manager, Now);
        await Assert.That(manager.Remove(2)).IsFalse();
        await Assert.That(manager.Remove(1)).IsTrue();
        rig.Tick(manager, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
    }

    [Test]
    public async Task PreexistingAndReplacementEffectsAreNeverRemoved()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        var original = new BuffTemplate { Id = 13816 };
        rig.Effects[13816] = new Buff(rig.Hull, rig.Hull, new SkillCasterUnit(10), original, null, Now);
        manager.Place(1, Vector3.Zero, 2, 50, Now);
        rig.Tick(manager, Now);
        rig.Effects[13817] = new Buff(rig.Hull, rig.Hull, new SkillCasterUnit(10),
            new BuffTemplate { Id = 13817 }, null, Now);
        rig.Tick(manager, Now.AddSeconds(2));
        await Assert.That(rig.Effects.Count).IsEqualTo(2);
        await Assert.That(rig.Removals.Count).IsEqualTo(0);
    }

    [Test]
    public async Task NaturalHarborTakesOverAndInstanceDisposalCleansOnlyOwnedEffects()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        manager.Place(1, Vector3.Zero, 20, 50, Now);
        rig.Tick(manager, Now);
        rig.Tick(manager, Now, natural: true);
        manager.Clear();
        await Assert.That(rig.Effects.Count).IsEqualTo(2);
        rig.Effects.Clear();
        manager.Place(1, Vector3.Zero, 20, 50, Now);
        rig.Tick(manager, Now);
        manager.Clear();
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
    }

    [Test]
    public async Task OtherInstanceAndLandVehiclesAreUnaffected()
    {
        var world = new WorldInstance(new WorldTemplate { Name = "main_world" }, 0, true, 1);
        var other = new WorldInstance(world.Template, 0, true, 2);
        var rig = new Rig();
        world.TemporaryEziAreas.Place(1, Vector3.Zero, 20, 50, Now);
        rig.Tick(other.TemporaryEziAreas, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
        rig.Hull.Template.SlaveKind = SlaveKind.Machine;
        rig.Tick(world.TemporaryEziAreas, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(0);
    }

    [Test]
    public async Task InvalidReplacementDoesNotDestroyExistingArea()
    {
        var manager = new TemporaryEziAreaManager();
        var rig = new Rig();
        manager.Place(1, Vector3.Zero, 20, 50, Now);
        await Assert.That(() => manager.Place(1, Vector3.Zero, -1, 50, Now)).Throws<ArgumentOutOfRangeException>();
        await Assert.That(() => manager.Place(1, Vector3.Zero, 20, float.NaN, Now)).Throws<ArgumentOutOfRangeException>();
        await Assert.That(() => manager.Place(1, new Vector3(float.PositiveInfinity, 0, 0), 20, 50, Now)).Throws<ArgumentOutOfRangeException>();
        rig.Tick(manager, Now);
        await Assert.That(rig.Effects.Count).IsEqualTo(2);
    }
}

