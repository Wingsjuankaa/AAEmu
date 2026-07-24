using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class ItemEnchantRatioGroup
    {
        public int Id { get; set; }
        public int ItemImplId { get; set; }
        public int KindId { get; set; }
    }

    public sealed class ItemEnchantRatio
    {
        public int GroupId { get; set; }
        public int Grade { get; set; }
        public int Success { get; set; }
        public int GreatSuccess { get; set; }
        public int Break { get; set; }
        public int Downgrade { get; set; }
        public int Cost { get; set; }
        public int DowngradeMin { get; set; }
        public int DowngradeMax { get; set; }
        public int CurrencyId { get; set; }
        public int Disable { get; set; }
    }

    public sealed class ItemGradeEnchantingSupportDefinition
    {
        public uint ItemId { get; set; }
        public int AddBreakMultiplier { get; set; }
        public int AddBreakRatio { get; set; }
        public int AddDisableMultiplier { get; set; }
        public int AddDisableRatio { get; set; }
        public int AddDowngradeMultiplier { get; set; }
        public int AddDowngradeRatio { get; set; }
        public int AddGreatSuccessGrade { get; set; }
        public int AddGreatSuccessMultiplier { get; set; }
        public int AddGreatSuccessRatio { get; set; }
        public int AddSuccessMultiplier { get; set; }
        public int AddSuccessRatio { get; set; }
        public int Icons { get; set; }
        public int ImplementationFlags { get; set; }
        public int RequiredScaleMaxId { get; set; }
        public int RequiredScaleMinId { get; set; }
        public int RequiredGradeMax { get; set; }
        public int RequiredGradeMin { get; set; }
    }

    public sealed class ItemRegradeProfile
    {
        public uint ItemId { get; set; }
        public int GroupId { get; set; }
        public ItemEnchantRatioGroup Group { get; set; }
        public ItemEnchantRatio Ratio { get; set; }
        public ItemGradeEnchantingSupportDefinition Support { get; set; }

        public bool HasNativeRatio => Group != null && Ratio != null;
    }

    public interface IItemRegradeRuleService
    {
        bool NativeCatalogueAvailable { get; }
        bool NativeMutationEnabled { get; }
        void Clear();
        void MarkNativeCatalogueAvailable();
        void RegisterGroup(ItemEnchantRatioGroup group);
        void RegisterRatio(ItemEnchantRatio ratio);
        void RegisterItem(uint itemId, int groupId);
        void RegisterSupport(ItemGradeEnchantingSupportDefinition support);
        ItemRegradeProfile GetProfile(uint itemId, int grade);
        ItemGradeEnchantingSupportDefinition GetSupport(uint itemId);
    }

    /// <summary>
    /// Read-only authority for native AA8 regrade ratios and support items.
    /// Economic mutation stays disabled until its transaction and result
    /// protocol are confirmed end-to-end.
    /// </summary>
    public sealed class ItemRegradeRuleService : IItemRegradeRuleService
    {
        private readonly Dictionary<int, ItemEnchantRatioGroup> _groups = new();
        private readonly Dictionary<(int GroupId, int Grade), ItemEnchantRatio>
            _ratios = new();
        private readonly Dictionary<uint, int> _itemGroups = new();
        private readonly Dictionary<uint, ItemGradeEnchantingSupportDefinition>
            _supports = new();

        public static ItemRegradeRuleService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }
        public bool NativeMutationEnabled => false;

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _groups.Clear();
            _ratios.Clear();
            _itemGroups.Clear();
            _supports.Clear();
        }

        public void MarkNativeCatalogueAvailable()
        {
            NativeCatalogueAvailable = true;
        }

        public void RegisterGroup(ItemEnchantRatioGroup group)
        {
            if (group != null)
                _groups[group.Id] = group;
        }

        public void RegisterRatio(ItemEnchantRatio ratio)
        {
            if (ratio != null)
                _ratios[(ratio.GroupId, ratio.Grade)] = ratio;
        }

        public void RegisterItem(uint itemId, int groupId)
        {
            if (groupId > 0)
                _itemGroups[itemId] = groupId;
        }

        public void RegisterSupport(ItemGradeEnchantingSupportDefinition support)
        {
            if (support != null)
                _supports[support.ItemId] = support;
        }

        public ItemRegradeProfile GetProfile(uint itemId, int grade)
        {
            _itemGroups.TryGetValue(itemId, out var groupId);
            _groups.TryGetValue(groupId, out var group);
            _ratios.TryGetValue((groupId, grade), out var ratio);
            _supports.TryGetValue(itemId, out var support);
            return new ItemRegradeProfile
            {
                ItemId = itemId,
                GroupId = groupId,
                Group = group,
                Ratio = ratio,
                Support = support
            };
        }

        public ItemGradeEnchantingSupportDefinition GetSupport(uint itemId)
        {
            return _supports.TryGetValue(itemId, out var support) ? support : null;
        }
    }
}
