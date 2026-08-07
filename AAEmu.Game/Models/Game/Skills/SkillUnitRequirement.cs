using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills
{
    /// <summary>
    /// AA8 unit requirement. Only kinds whose server contract is demonstrated
    /// are evaluated; unsupported kinds remain outside the executable closure
    /// instead of being guessed.
    /// </summary>
    public sealed class SkillUnitRequirement
    {
        public const uint EquipRangedKind = 29;
        public const uint NoBuffTagKind = 30;
        public const uint TargetHealthLessThanKind = 26;
        public const uint BowHoldableId = 19;
        public const uint ShotgunHoldableId = 31;

        public uint OwnerId { get; set; }
        public uint KindId { get; set; }
        public uint Value1 { get; set; }
        public uint Value2 { get; set; }
        public uint Value3 { get; set; }
        public bool DisplayMessage { get; set; }

        public bool IsSkillSupported =>
            KindId == EquipRangedKind || KindId == NoBuffTagKind;
        public bool IsTargetSupported => KindId == TargetHealthLessThanKind;
        public bool IsSupported => IsSkillSupported || IsTargetSupported;

        public SkillResult Validate(Unit caster)
        {
            switch (KindId)
            {
                case EquipRangedKind:
                    var ranged = caster?.Equipment?.GetItemBySlot((int)EquipmentItemSlot.Ranged);
                    var holdableId = (ranged?.Template as WeaponTemplate)?.HoldableTemplate?.Id ?? 0;
                    return MatchesEquipRanged(Value1, holdableId)
                        ? SkillResult.Success
                        : SkillResult.UrkEquipRanged;
                case NoBuffTagKind:
                    return MatchesNoBuffTag(caster?.Buffs?.CheckBuffTag(Value1) == true)
                        ? SkillResult.Success
                        : SkillResult.UrkNoBuffTag;
                default:
                    return SkillResult.Success;
            }
        }

        public static bool MatchesEquipRanged(uint requirementValue, uint holdableId)
        {
            switch (requirementValue)
            {
                case 0:
                    return holdableId == BowHoldableId;
                case 2:
                    return holdableId == ShotgunHoldableId;
                default:
                    return false;
            }
        }

        public static bool MatchesNoBuffTag(bool hasForbiddenTag) => !hasForbiddenTag;

        /// <summary>
        /// AA8 PlotCondition-owned kind 26. value1=1 selects percentage mode,
        /// value2 is the strict upper threshold. The first recovered consumer
        /// is Archery Snipe: Flame (condition 14753, target HP &lt; 30%).
        /// </summary>
        public bool ValidateTarget(Unit target)
        {
            if (KindId != TargetHealthLessThanKind || target == null)
                return false;

            return MatchesTargetHealthLessThan(
                target.Hp,
                target.MaxHp,
                Value1,
                Value2);
        }

        public static bool MatchesTargetHealthLessThan(
            int hp,
            int maxHp,
            uint percentageMode,
            uint threshold)
        {
            if (percentageMode == 1)
                return maxHp > 0 && (long)hp * 100 < (long)maxHp * threshold;

            return hp < threshold;
        }
    }
}
