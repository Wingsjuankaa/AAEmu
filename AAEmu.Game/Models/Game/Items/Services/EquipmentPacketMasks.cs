namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>AA8 equipment masks preserve physical slot indexes in two uint32 fields.</summary>
public static class EquipmentPacketMasks
{
    public const int PhysicalSlotCount = 32;

    public static uint BuildValidFlags(IReadOnlyList<Item> items)
    {
        uint flags = 0;
        var count = Math.Min(items?.Count ?? 0, PhysicalSlotCount);
        for (var slot = 0; slot < count; slot++)
        {
            if (items![slot] != null)
                flags |= 1u << slot;
        }
        return flags;
    }

    public static uint BuildItemFlags(IReadOnlyList<Item> items)
    {
        uint flags = 0;
        var count = Math.Min(items?.Count ?? 0, PhysicalSlotCount);
        for (var slot = 0; slot < count; slot++)
        {
            if (items![slot] is { ItemFlags: not ItemFlag.None })
                flags |= 1u << slot;
        }
        return flags;
    }
}
