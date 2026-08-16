using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Items;

// (called with the unit's idType) and the character-list lobby record (called with mode 0 = Character).
// Wire: validFlags u64 (bit i set iff slot i is occupied, over 34 slots) + each occupied slot in order
// (empty slots emit nothing) plus, for a Character, a trailing per-slot flags u64. Per-slot form depends on
// the unit type and slot range: body-image slots 19-25 (non-Slave) write templateId only; an Npc writes a
// compact {templateId, id, grade} for normal slots and a full item for 27/31-33. Character, Slave,
// Housing, Mate, and type 7 write full items; Transfer and Shipyard have no normal-slot branch.
public static class EquipmentSerializer
{
    public const int SlotCount = 34; // 10.0.2.13 equip-slot count (AAEmu fills 0..27; 28..33 stay empty)

    /// <summary>
    /// Builds the r575 per-slot equipment-modifier activation mask. AAEmu only accepts usable
    /// items into the physical equipment container, so every occupied physical slot is active.
    /// This is distinct from the changed-entry mask used by SCUnitEquipmentsChanged.
    /// </summary>
    public static ulong GetActivationFlags(Unit unit)
    {
        if (unit?.Equipment == null)
            return 0;

        ulong flags = 0;
        for (var slot = 0; slot < SlotCount; slot++)
        {
            if (unit.Equipment.GetItemBySlot(slot) != null)
                flags |= 1UL << slot;
        }

        return flags;
    }

    public static void Write(PacketStream stream, Unit unit, BaseUnitType baseUnitType)
    {
        var validFlags = GetActivationFlags(unit);
        stream.Write(validFlags);

        for (var i = 0; i < SlotCount; i++)
        {
            var item = unit.Equipment.GetItemBySlot(i);
            if (item == null)
                continue; // empty slots emit nothing in v10 (validFlags already marked them)

            if (i is >= 19 and <= 25 && baseUnitType != BaseUnitType.Slave)
            {
                stream.Write(item.TemplateId); // body-image slots: templateId only
            }
            else if (baseUnitType == BaseUnitType.Npc)
            {
                if (i == 27 || i is >= 31 and <= 33)
                {
                    stream.Write(item); // full item
                }
                else
                {
                    stream.Write(item.TemplateId); // compact item
                    stream.Write(item.Id);
                    stream.Write(item.Grade);
                }
            }
            else if (baseUnitType is BaseUnitType.Character or BaseUnitType.Slave or
                     BaseUnitType.Housing or BaseUnitType.Mate)
            {
                stream.Write(item);
            }
        }

        if (baseUnitType == BaseUnitType.Character)
            stream.Write(validFlags);
    }
}
