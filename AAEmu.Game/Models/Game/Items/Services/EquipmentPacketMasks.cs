using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Items.Services
{
    /// <summary>
    /// AA8 equipment state is represented by two one-bit-per-physical-slot
    /// masks. Empty slots must retain their physical index.
    /// </summary>
    public static class EquipmentPacketMasks
    {
        public const int PhysicalSlotCount = 32;

        public static uint BuildValidFlags(IReadOnlyList<Item> items)
        {
            uint flags = 0;
            var count = items == null ? 0 : System.Math.Min(items.Count, PhysicalSlotCount);
            for (var slot = 0; slot < count; slot++)
            {
                if (items[slot] != null)
                    flags |= 1u << slot;
            }

            return flags;
        }

        public static uint BuildItemFlags(IReadOnlyList<Item> items)
        {
            uint flags = 0;
            var count = items == null ? 0 : System.Math.Min(items.Count, PhysicalSlotCount);
            for (var slot = 0; slot < count; slot++)
            {
                // x2game stores one state bit for each physical position. ItemFlag
                // remains an item-detail byte; it must never be shifted wholesale
                // into this 32-bit equipment mask.
                if (items[slot] != null && items[slot].ItemFlags != ItemFlag.None)
                    flags |= 1u << slot;
            }

            return flags;
        }
    }
}
