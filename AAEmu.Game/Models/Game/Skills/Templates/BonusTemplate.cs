using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Templates
{
    public class BonusTemplate
    {
        public UnitAttribute Attribute { get; set; }
        public UnitModifierType ModifierType { get; set; }
        public long Value { get; set; }
        public int DynamicValue { get; set; }
        public int LinearLevelBonus { get; set; }
    }
}
