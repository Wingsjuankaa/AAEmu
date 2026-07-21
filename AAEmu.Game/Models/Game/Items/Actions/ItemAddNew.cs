using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class ItemAddNew : ItemTask
    {
        private readonly Item _item;

        public ItemAddNew(Item item)
        {
            _item = item;
            _type = ItemAction.ChangeOwner; // 16 in the 8.0 protocol
            _logType = ItemTaskLogType.GainItem;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);

            stream.Write((byte)_item.SlotType);
            stream.Write((byte)_item.Slot);
            WriteItemDetails(stream, _item);
            return stream;
        }
    }
}
