using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class ItemSalvagingCoverage
    {
        public uint ItemId { get; set; }
        public int ReagentDefinitions { get; set; }
        public int ProductDefinitions { get; set; }
        public int SmeltingDefinitions { get; set; }

        public bool HasConversionDefinition =>
            ReagentDefinitions > 0 || ProductDefinitions > 0;

        public bool HasSmeltingDefinition => SmeltingDefinitions > 0;
    }

    public interface IItemSalvagingCatalogueService
    {
        bool NativeCatalogueAvailable { get; }
        void Clear();
        void MarkNativeCatalogueAvailable();
        void RegisterReagent(uint itemId);
        void RegisterProduct(uint itemId);
        void RegisterSmeltingItem(uint itemId);
        ItemSalvagingCoverage GetCoverage(uint itemId);
    }

    /// <summary>
    /// Read-only coverage index over the native AA8 item-conversion and
    /// smelting graph. It intentionally does not infer a conversion outcome.
    /// </summary>
    public sealed class ItemSalvagingCatalogueService
        : IItemSalvagingCatalogueService
    {
        private readonly Dictionary<uint, int> _reagents = new();
        private readonly Dictionary<uint, int> _products = new();
        private readonly Dictionary<uint, int> _smeltingItems = new();

        public static ItemSalvagingCatalogueService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _reagents.Clear();
            _products.Clear();
            _smeltingItems.Clear();
        }

        public void MarkNativeCatalogueAvailable()
        {
            NativeCatalogueAvailable = true;
        }

        public void RegisterReagent(uint itemId)
        {
            Increment(_reagents, itemId);
        }

        public void RegisterProduct(uint itemId)
        {
            Increment(_products, itemId);
        }

        public void RegisterSmeltingItem(uint itemId)
        {
            Increment(_smeltingItems, itemId);
        }

        public ItemSalvagingCoverage GetCoverage(uint itemId)
        {
            _reagents.TryGetValue(itemId, out var reagents);
            _products.TryGetValue(itemId, out var products);
            _smeltingItems.TryGetValue(itemId, out var smeltingItems);
            return new ItemSalvagingCoverage
            {
                ItemId = itemId,
                ReagentDefinitions = reagents,
                ProductDefinitions = products,
                SmeltingDefinitions = smeltingItems
            };
        }

        private static void Increment(Dictionary<uint, int> values, uint itemId)
        {
            if (itemId == 0)
                return;
            values.TryGetValue(itemId, out var count);
            values[itemId] = count + 1;
        }
    }
}
