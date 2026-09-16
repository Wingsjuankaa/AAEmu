using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>Session-only GM additions; never occupy a gear/buff index or enter persistence.</summary>
public sealed class GmStatBonuses
{
    public sealed record Definition(string Name, UnitAttribute Attribute, int Scale, int Maximum);

    public static readonly IReadOnlyList<Definition> Definitions = Array.AsReadOnly(new[]
    {
        new Definition("strength", UnitAttribute.Str, 1, 100000),
        new Definition("agility", UnitAttribute.Dex, 1, 100000),
        new Definition("stamina", UnitAttribute.Sta, 1, 100000),
        new Definition("intelligence", UnitAttribute.Int, 1, 100000),
        new Definition("spirit", UnitAttribute.Spi, 1, 100000),
        new Definition("health", UnitAttribute.MaxHealth, 1, 1000000),
        new Definition("mana", UnitAttribute.MaxMana, 1, 1000000),
        new Definition("armor", UnitAttribute.Armor, 1, 100000),
        new Definition("resistance", UnitAttribute.MagicResist, 1, 100000),
        new Definition("melee_power", UnitAttribute.MeleeDpsInc, 1000, 100000),
        new Definition("ranged_power", UnitAttribute.RangedDpsInc, 1000, 100000),
        new Definition("spell_power", UnitAttribute.SpellDpsInc, 1000, 100000),
        new Definition("healing_power", UnitAttribute.HealDpsInc, 1000, 100000),
        // AA10 damage multipliers are (1000 + flat bonuses) / 1000.
        new Definition("melee_damage", UnitAttribute.MeleeDamageMul, 10, 10000),
        new Definition("ranged_damage", UnitAttribute.RangedDamageMul, 10, 10000),
        new Definition("spell_damage", UnitAttribute.SpellDamageMul, 10, 10000)
    });

    private readonly Dictionary<UnitAttribute, int> _values = [];
    private readonly object _lock = new();

    public static Definition Find(string name) => Definitions.FirstOrDefault(d =>
        d.Name.Equals(name, StringComparison.OrdinalIgnoreCase));

    public bool Set(string name, int value)
    {
        var definitions = name.Equals("damage", StringComparison.OrdinalIgnoreCase)
            ? Definitions.Where(d => d.Name.EndsWith("_damage", StringComparison.Ordinal)).ToArray()
            : Definitions.Where(d => d.Name.Equals(name, StringComparison.OrdinalIgnoreCase)).ToArray();
        if (definitions.Length == 0 || value < 0 || definitions.Any(d => value > d.Maximum))
            return false;
        lock (_lock)
        {
            foreach (var definition in definitions)
            {
                if (value == 0)
                    _values.Remove(definition.Attribute);
                else
                    _values[definition.Attribute] = value;
            }
        }
        return true;
    }

    public void Clear()
    {
        lock (_lock)
            _values.Clear();
    }

    public int Get(UnitAttribute attribute)
    {
        lock (_lock)
            return _values.GetValueOrDefault(attribute);
    }

    public Bonus GetBonus(UnitAttribute attribute)
    {
        var value = Get(attribute);
        if (value == 0)
            return null;
        var definition = Definitions.First(d => d.Attribute == attribute);
        return new Bonus
        {
            Template = new BonusTemplate { Attribute = attribute, ModifierType = UnitModifierType.Value },
            Value = checked((long)value * definition.Scale)
        };
    }
}
