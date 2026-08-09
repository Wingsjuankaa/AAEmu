using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class ItemRemove : ItemTask
    {
        private readonly ulong _itemId;
        private readonly SlotType _slotType;
        private readonly byte _slot;
        private readonly int _count;
        private readonly uint _templateId;

        public ItemRemove(Item item)
        {
            _type = ItemAction.Remove;

            _itemId = item.Id;
            _slotType = item.SlotType;
            _slot = (byte)item.Slot;
            _count = item.Count;
            _templateId = item.TemplateId;
            _logType = item.SlotType == SlotType.Equipment
                ? ItemTaskLogType.Place
                : ItemTaskLogType.RemoveItem;
        }

        public ItemRemove(ulong itemId, SlotType slotType, byte slot, uint templateId)
        {
            _type = ItemAction.Remove;
            _itemId = itemId;
            _slotType = slotType;
            _slot = slot;
            _count = 0;
            _templateId = templateId;
            _logType = slotType == SlotType.Equipment
                ? ItemTaskLogType.Place
                : ItemTaskLogType.RemoveItem;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);

            stream.Write((byte)_slotType);
            stream.Write(_slot);
            stream.Write(_itemId);
            stream.Write(_count);
            stream.Write(System.DateTime.MinValue); // removeReservationTime
            stream.Write(_templateId);
            stream.Write((uint)0); // dbSlaveId
            stream.Write((uint)0); // type
            return stream;
        }
    }
}
