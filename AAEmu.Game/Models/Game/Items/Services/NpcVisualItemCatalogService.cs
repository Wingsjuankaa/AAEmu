using System;
using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Items.Services
{
    /// <summary>
    /// Presentation-only allow-list for item ids referenced by native AA8 NPC
    /// equipment packs and body-part descriptors.
    ///
    /// This catalogue does not promote an item definition for inventory,
    /// persistence, ItemTask, crafting, loot, or player equipment use.
    /// </summary>
    public sealed class NpcVisualItemCatalogService
    {
        private readonly HashSet<uint> _itemIds = new HashSet<uint>();

        public static NpcVisualItemCatalogService Instance { get; } =
            new NpcVisualItemCatalogService();

        public bool CatalogueAvailable { get; private set; }
        public int Count => _itemIds.Count;

        public void Clear()
        {
            _itemIds.Clear();
            CatalogueAvailable = false;
        }

        public void Register(uint itemId)
        {
            if (itemId == 0)
                throw new ArgumentOutOfRangeException(nameof(itemId));

            _itemIds.Add(itemId);
            CatalogueAvailable = true;
        }

        public bool CanCreatePresentationItem(uint itemId)
        {
            return _itemIds.Contains(itemId);
        }
    }
}
