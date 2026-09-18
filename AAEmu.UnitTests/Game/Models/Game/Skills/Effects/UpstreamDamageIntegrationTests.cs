using AAEmu.Game;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Effects;

[NotInParallel]
public class UpstreamDamageIntegrationTests
{
    private sealed class Victim : Unit
    {
        public List<DamageType> ReceivedTypes { get; } = [];
        public override void ReduceCurrentHp(BaseUnit attacker, int value,
            KillReason killReason = KillReason.Damage, DamageType damageType = DamageType.Melee)
        {
            ReceivedTypes.Add(damageType);
            base.ReduceCurrentHp(attacker, value, killReason, damageType);
        }
    }

    [Test]
    [Arguments(DamageType.Magic)]
    [Arguments(DamageType.Ranged)]
    [Arguments(DamageType.Siege)]
    public async Task DamageEffectPreservesTypeAndRepeatedHits(DamageType damageType)
    {
        var previous = WorldIntegration.AllowsPlotSelfDamageBypass;
        try
        {
            var unit = new Victim
            {
                ObjId = 77, Faction = new SystemFaction { Id = (FactionsEnum)1 },
                Hp = 1000, MaxHp = 1000
            };
            WorldIntegration.AllowsPlotSelfDamageBypass = u => u == unit;
            var effect = new DamageEffect
            {
                Id = 6844, UseFixedDamage = true, FixedMin = 50, FixedMax = 50,
                Multiplier = 1f, DamageType = damageType
            };
            for (var index = 0; index < 3; index++)
            {
                effect.Apply(unit, new SkillCasterUnit(unit.ObjId), unit,
                    new SkillCastUnitTarget(unit.ObjId), new CastPlot(1705, 1, 13818, 28457),
                    new EffectSource(), null, DateTime.UtcNow);
                await Assert.That(unit.Hp).IsEqualTo(1000 - 50 * (index + 1));
            }
            await Assert.That(unit.ReceivedTypes.Count).IsEqualTo(3);
            await Assert.That(unit.ReceivedTypes.All(type => type == damageType)).IsTrue();
        }
        finally
        {
            WorldIntegration.AllowsPlotSelfDamageBypass = previous;
        }
    }
}
