using System;

namespace AAEmu.Game.Models.Game.Items.Templates
{
    public class EquipItemTemplate : ItemTemplate
    {
        public override Type ClassType => typeof(EquipItem);

        public uint ModSetId { get; set; }
        public bool Repairable { get; set; }
        public int DurabilityMultiplier { get; set; }
        public uint RechargeBuffId { get; set; }
        public int ChargeLifetime { get; set; }
        public int ChargeCount { get; set; }
        public ItemLookConvert ItemLookConvert { get; set; }
        public uint EquipItemSetId { get; set; }
        public uint EnhancedItemMaterialId { get; set; }
        public uint ItemRndAttrCategoryId { get; set; }
        public bool OrUnitRequirements { get; set; }
        public uint RechargeRestrictItemId { get; set; }
        public uint RechargeRndAttrUnitModifierRestrictItemId { get; set; }
        public int RndAttrUnitModifierLifetime { get; set; }
        public uint SkinKindId { get; set; }
        public bool UseAsStat { get; set; }
    }
}
