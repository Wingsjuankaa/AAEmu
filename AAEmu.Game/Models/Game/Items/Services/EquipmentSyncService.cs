using System;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public interface IEquipmentSyncService
    {
        void Resync(Character character);
        void Resync(Character character, SlotType container);
    }

    public sealed class EquipmentSyncService : IEquipmentSyncService
    {
        public static EquipmentSyncService Instance { get; } = new EquipmentSyncService();

        public void Resync(Character character)
        {
            if (character == null)
                return;

            var state = new (byte slot, Item item)[EquipmentPacketMasks.PhysicalSlotCount];
            for (byte slot = 0; slot < EquipmentPacketMasks.PhysicalSlotCount; slot++)
                state[slot] = (slot, character.Inventory.Equipment.GetItemBySlot(slot));

            character.BroadcastPacket(
                new SCUnitEquipmentsChangedPacket(character.ObjId, state),
                false);
        }

        public void Resync(Character character, SlotType container)
        {
            if (character == null)
                return;

            if (container == SlotType.Equipment)
            {
                Resync(character);
                return;
            }

            character.Inventory.SendAuthoritativeContainer(container);
        }
    }
}
