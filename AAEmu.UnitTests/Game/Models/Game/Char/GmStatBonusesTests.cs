using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class GmStatBonusesTests
{
    [Test]
    public async Task DamageUsesCombatGettersAndReplacementDoesNotStack()
    {
        var character = new Character(null);
        await Assert.That(character.GmStats.Set("damage", 900)).IsTrue();
        await Assert.That(character.MeleeDamageMul).IsEqualTo(10f);
        await Assert.That(character.RangedDamageMul).IsEqualTo(10f);
        await Assert.That(character.SpellDamageMul).IsEqualTo(10f);
        character.GmStats.Set("DAMAGE", 100);
        await Assert.That(character.SpellDamageMul).IsEqualTo(2f);
        character.GmStats.Set("spell_damage", 0);
        await Assert.That(character.SpellDamageMul).IsEqualTo(1f);
        await Assert.That(character.MeleeDamageMul).IsEqualTo(2f);
    }

    [Test]
    public async Task ResetKeepsGearAndBuffBonusesAndOtherSessionsUntouched()
    {
        var character = new Character(null);
        var other = new Character(null);
        character.AddBonus(1, new Bonus { Value = 30, Template = new BonusTemplate
            { Attribute = UnitAttribute.Str, ModifierType = UnitModifierType.Value } });
        character.AddBonus(2, new Bonus { Value = 20, Template = new BonusTemplate
            { Attribute = UnitAttribute.Str, ModifierType = UnitModifierType.Value } });
        character.GmStats.Set("strength", 1000);
        await Assert.That(character.CalculateWithBonuses(10, UnitAttribute.Str)).IsEqualTo(1060d);
        await Assert.That(other.CalculateWithBonuses(10, UnitAttribute.Str)).IsEqualTo(10d);
        character.GmStats.Clear();
        await Assert.That(character.CalculateWithBonuses(10, UnitAttribute.Str)).IsEqualTo(60d);
        await Assert.That(character.Bonuses.Count).IsEqualTo(2);
        await Assert.That(new Character(null).GmStats.Get(UnitAttribute.Str)).IsEqualTo(0);
    }

    [Test]
    public async Task InvalidValuesDoNotPartiallyReplaceDamageGroup()
    {
        var stats = new GmStatBonuses();
        stats.Set("damage", 300);
        foreach (var value in new[] { -1, 10001, int.MaxValue })
            await Assert.That(stats.Set("damage", value)).IsFalse();
        await Assert.That(stats.Set("not_a_stat", 10)).IsFalse();
        foreach (var attr in new[] { UnitAttribute.MeleeDamageMul, UnitAttribute.RangedDamageMul, UnitAttribute.SpellDamageMul })
            await Assert.That(stats.Get(attr)).IsEqualTo(300);
    }

    [Test]
    public async Task PowersUseThousandthsAndDamageUsesPermille()
    {
        var character = new Character(null);
        character.GmStats.Set("spell_power", 2500);
        character.GmStats.Set("spell_damage", 250);
        await Assert.That(character.CalculateWithBonuses(0, UnitAttribute.SpellDpsInc)).IsEqualTo(2500000d);
        await Assert.That(character.SpellDamageMul).IsEqualTo(3.5f);
        character.GmStats.Set("health", 1000000);
        await Assert.That(character.CalculateWithBonuses(10000, UnitAttribute.MaxHealth)).IsEqualTo(1010000d);
    }
}
