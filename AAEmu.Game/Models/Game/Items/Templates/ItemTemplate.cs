using System;

namespace AAEmu.Game.Models.Game.Items.Templates
{
    public enum ItemBindType
    {
        Normal = 1,
        BindOnPickup = 2,
        BindOnEquip = 3,
        BindOnUnpack = 4,
        BindOnPickupPack = 5,
        BindOnAuctionWin = 6,
    }
    
    public class ItemTemplate
    {
        public virtual Type ClassType => typeof(Item);

        public uint Id { get; set; }
        /// <summary>
        /// Original Korean name is stored here, use LocalizationManager to get the names for other langauges
        /// </summary>
        public string Name { get; set; }
        public int Category_Id { get; set; }
        public int Level { get; set; }
        public int Price { get; set; }
        public int Refund { get; set; }
        public ItemBindType BindType { get; set; }
        public int PickupLimit { get; set; }
        public int MaxCount { get; set; }
        public bool Sellable { get; set; }
        public uint UseSkillId { get; set; }
        public bool UseSkillAsReagent { get; set; }
        public uint BuffId { get; set; }
        public bool Gradable { get; set; }
        public bool LootMulti { get; set; }
        public uint LootQuestId { get; set; }
        public int HonorPrice { get; set; }
        public int ExpAbsLifetime { get; set; }
        public int ExpOnlineLifetime { get; set; }
        public int ExpDate { get; set; }
        public int LevelRequirement { get; set; }
        public int AuctionCategoryA {get; set; }
        public int AuctionCategoryB { get; set; }
        public int AuctionCategoryC { get; set; }
        public int LevelLimit { get; set; }
        public int FixedGrade { get; set; }
        public int LivingPointPrice { get; set; }
        public byte CharGender { get; set; }
        public int ActabilityGroupId { get; set; }
        public int ActabilityRequirement { get; set; }
        public int AuctionCharge { get; set; }
        public bool AuctionChargeDefault { get; set; }
        public bool AuctionOnly { get; set; }
        public bool AutoComplete { get; set; }
        public bool AutoLoot { get; set; }
        public bool AutoRegisterToActionbar { get; set; }
        public bool CashItem { get; set; }
        public int ContributionPointPrice { get; set; }
        public int CraftId { get; set; }
        public bool Disenchantable { get; set; }
        public long ExpirationDate { get; set; }
        public int ExpDayOfWeekId { get; set; }
        public int ExpDayOfWeekMinute { get; set; }
        public int ExpeditionLevel { get; set; }
        public int IconId { get; set; }
        public int ImplId { get; set; }
        public int IngameShopMainCategory { get; set; }
        public int IngameShopSubCategory { get; set; }
        public int LimitedSaleCount { get; set; }
        public int MaleIconId { get; set; }
        public int MaxEnchantScaleId { get; set; }
        public int MaxEnchantableGrade { get; set; }
        public bool NotifyUi { get; set; }
        public bool OneTimeSale { get; set; }
        public int OverIconId { get; set; }
        public int PickupSoundId { get; set; }
        public int ProcLifetime { get; set; }
        public uint ProcRechargeRestrictItemId { get; set; }
        public bool SideEffect { get; set; }
        public int SpecialtyZoneId { get; set; }
        public long Uid { get; set; }
        public int UseOrEquipmentSoundId { get; set; }
        public int UseSkillLifetime { get; set; }
        public uint UseSkillRechargeRestrictItemId { get; set; }

        // Helpers
        public string searchString { get; set; }
    }
}
