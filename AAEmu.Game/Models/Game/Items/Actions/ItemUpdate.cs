using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class ItemUpdate : ItemTask
    {
        private readonly Item _item;

        public ItemUpdate(Item item)
        {
            _type = ItemAction.UpdateDetail;
            _item = item;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);

            stream.Write((byte)_item.SlotType);
            stream.Write((byte)_item.Slot);

            stream.Write(_item.Id);
            _item.WriteUpdateDetailBlock(stream);
            return stream;
        }
    }
}
