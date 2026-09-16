using AAEmu.Game;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Slaves;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Units;

[NotInParallel]
public class ShipPropulsionTests
{
    // AA10: hull 578 flat 100, engine buff 16149 flat 1000 + HP 5000.
    // Zone RVA 0xBF7150 contributes zero to attribute 10; 0x227140 divides it by 1000.
    private static Hull FishingHull()
    {
        var hull = new Hull { ObjId = 1389, Template = new SlaveTemplate { SlaveKind = SlaveKind.Fishboat } };
        hull.AddBonus(1, new Bonus { Template = Flat(UnitAttribute.MoveSpeedMul, 100), Value = 100 });
        return hull;
    }

    private static BonusTemplate Flat(UnitAttribute attribute, long value) =>
        new() { Attribute = attribute, ModifierType = UnitModifierType.Value, Value = value };

    private static Buff Engine(Hull hull, long rating, bool passive = true)
    {
        var template = new BuffTemplate { Id = 16149 };
        template.Bonuses.Add(Flat(UnitAttribute.MoveSpeedMul, rating));
        template.Bonuses.Add(Flat(UnitAttribute.MaxHealth, 5000));
        return new Buff(hull, hull, new SkillCasterUnit(hull.ObjId), template, null, DateTime.UtcNow)
        { Index = 2, Passive = passive, Stack = 1, AbLevel = 1 };
    }

    [Test]
    public async Task MissingEngine_LeavesOnlyTheNativeHullContribution()
    {
        var hull = FishingHull();
        await Assert.That(hull.MoveSpeedMul).IsEqualTo(0.1f);
        await Assert.That(13f * hull.MoveSpeedMul).IsEqualTo(13f * 0.1f);
    }

    [Test]
    [Arguments(1000L, 1.1f)]
    [Arguments(1050L, 1.15f)]
    [Arguments(1550L, 1.65f)]
    public async Task Engine_AddsItsFullRatingWithoutInventingABaseline(long rating, float expected)
    {
        var hull = FishingHull();
        var engine = Engine(hull, rating);
        engine.Template.Start(hull, hull, engine);
        engine.Template.Start(hull, hull, engine); // Refresh must not duplicate the engine.
        await Assert.That(hull.MoveSpeedMul).IsEqualTo(expected);
        await Assert.That(hull.GetBonuses(UnitAttribute.MoveSpeedMul).Count).IsEqualTo(2);
        hull.RemoveBonus(engine.Index, UnitAttribute.MoveSpeedMul);
        await Assert.That(hull.MoveSpeedMul).IsEqualTo(0.1f);
    }

    [Test]
    public async Task OrdinaryUnitAndLandVehicle_KeepTheirExistingMovementBaseline()
    {
        await Assert.That(new Unit().MoveSpeedMul).IsEqualTo(1f);
        await Assert.That(new Slave { Template = new SlaveTemplate { SlaveKind = SlaveKind.Machine } }.MoveSpeedMul)
            .IsEqualTo(1f);
    }

    [Test]
    public async Task SailTrim_AddsEveryStackToTheHull()
    {
        var hull = FishingHull();
        var engine = Engine(hull, 1000);
        engine.Template.Start(hull, hull, engine);
        var trim = new BuffTemplate { Id = 2 };
        trim.Bonuses.Add(Flat(UnitAttribute.MoveSpeedMul, 6));
        var buff = new Buff(hull, hull, new SkillCasterUnit(hull.ObjId), trim, null, DateTime.UtcNow)
        { Index = 3, Passive = true, Stack = 10, AbLevel = 1 };
        trim.Start(hull, hull, buff);
        await Assert.That(hull.MoveSpeedMul).IsEqualTo(1.16f);
    }

    [Test]
    public async Task InstallingBasicEngine_RelaysTheBuffToTheZone()
    {
        var oldAuthority = WorldIntegration.ZoneAuthority;
        var oldRelay = WorldIntegration.RelayBuffCreatedToZone;
        try
        {
            WorldIntegration.ZoneAuthority = true;
            var delivered = new List<(uint Owner, byte[] Body)>();
            WorldIntegration.RelayBuffCreatedToZone = (owner, body) => delivered.Add((owner, body));
            var hull = FishingHull();
            var engine = Engine(hull, 1000, passive: false);
            engine.Template.Start(hull, hull, engine);
            await Assert.That(delivered.Count).IsEqualTo(1);
            await Assert.That(delivered[0].Owner).IsEqualTo(hull.ObjId);
            await Assert.That(BuffCreatedWire.TryGetBuffIndex(delivered[0].Body, out var index)).IsTrue();
            await Assert.That(index).IsEqualTo(engine.Index);
            await Assert.That(engine.RelayedToZone).IsTrue();
        }
        finally
        {
            WorldIntegration.ZoneAuthority = oldAuthority;
            WorldIntegration.RelayBuffCreatedToZone = oldRelay;
        }
    }

    private sealed class Hull : Slave
    {
        public override void BroadcastPacket(GamePacket packet, bool self) { }
    }
}
