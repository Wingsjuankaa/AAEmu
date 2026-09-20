using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.Units;

[NotInParallel]
public class CombatResourceBonusTests
{
    [Before(Test)]
    public void Seed()
    {
        // AA10 unit_modifiers 80244/80245, owner_type CombatResource, owner_id 1.
        var resource = new CombatResource { Id = 1, Max = 5 };
        resource.Bonuses.Add(new BonusTemplate { Attribute = UnitAttribute.MeleeCriticalBonus, LinearLevelBonus = 5000 });
        resource.Bonuses.Add(new BonusTemplate { Attribute = UnitAttribute.AttackSpeedMul, LinearLevelBonus = 3000 });
        CombatResourceGameData.Instance.SeedForTests([resource], null);
    }

    [After(Test)]
    public void Clear() => CombatResourceGameData.Instance.ClearForTests();

    [Test]
    public async Task LoaderReadsOnlyEnabledResourceOwnedModifiers()
    {
        using var connection = new SqliteConnection("Data Source=:memory:");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE combat_resources (id INTEGER, name TEXT, max INTEGER, default_point INTEGER,
                resouece_send_type_id INTEGER, recovery_cycle INTEGER DEFAULT 0,
                peace_recovery_amount INTEGER DEFAULT 0, combat_recovery_amount INTEGER DEFAULT 0,
                etc_recovery_state_id INTEGER DEFAULT 1, etc_recovery_amount INTEGER DEFAULT 0,
                buff_id INTEGER DEFAULT 0, resource_buff_condition_id INTEGER DEFAULT 1);
            INSERT INTO combat_resources (id,name,max,default_point,resouece_send_type_id) VALUES (1, 'Delirium', 5, 0, 1);
            CREATE TABLE combat_resource_groups (ability_id INTEGER, combat_resource_1_id INTEGER,
                combat_resource_2_id INTEGER, change_combat_resource_1_id INTEGER, change_combat_resource_2_id INTEGER);
            CREATE TABLE unit_modifiers (owner_type TEXT, owner_id INTEGER, enable TEXT,
                unit_attribute_id INTEGER, unit_modifier_type_id INTEGER, value INTEGER, linear_level_bonus INTEGER);
            INSERT INTO unit_modifiers VALUES ('CombatResource',1,'t',17,0,0,5000),
                ('CombatResource',1,'t',218,0,0,3000), ('CombatResource',1,'f',218,0,999,0),
                ('Buff',1,'t',218,0,999,0), ('CombatResource',999,'t',218,0,999,0);
            """;
        command.ExecuteNonQuery();
        var data = new CombatResourceGameData();
        data.Load(connection);
        await Assert.That(data.Get(1).Bonuses.Count).IsEqualTo(2);
        await Assert.That(data.Get(1).Bonuses[0].LinearLevelBonus).IsEqualTo(5000);
        await Assert.That(data.Get(1).Bonuses[1].LinearLevelBonus).IsEqualTo(3000);
    }

    [Test]
    public async Task Delirium_GainCapSpendAndExpiryAffectAttributesImmediately()
    {
        var unit = new Unit();
        await Assert.That(unit.AttackSpeedRating).IsEqualTo(0L);
        unit.AddCombatResource(1, 1);
        await Assert.That(unit.AttackSpeedRating).IsEqualTo(30L);
        await Assert.That(unit.GetBonuses(UnitAttribute.MeleeCriticalBonus).Sum(b => b.Value)).IsEqualTo(50L);
        unit.AddCombatResource(1, 20);
        await Assert.That(unit.AttackSpeedRating).IsEqualTo(150L);
        await Assert.That(unit.GetBonuses(UnitAttribute.MeleeCriticalBonus).Sum(b => b.Value)).IsEqualTo(250L);
        unit.AddCombatResource(1, -1);
        await Assert.That(unit.AttackSpeedRating).IsEqualTo(120L);
        unit.AddCombatResource(1, -6); // AA10 recovery amount: clears all stacks.
        await Assert.That(unit.AttackSpeedRating).IsEqualTo(0L);
        await Assert.That(unit.GetBonuses(UnitAttribute.MeleeCriticalBonus).Count).IsEqualTo(0);
    }

    [Test]
    public async Task ResourcesArePerUnitAndDoNotNeedAnInventedBuff()
    {
        var first = new Unit();
        var second = new Unit();
        first.AddCombatResource(1, 2);
        second.AddCombatResource(9999, 5);
        await Assert.That(first.AttackSpeedRating).IsEqualTo(60L);
        await Assert.That(second.AttackSpeedRating).IsEqualTo(0L);
        await Assert.That(CombatResourceGameData.Instance.Get(1).BuffId).IsEqualTo(0u);
    }
}
