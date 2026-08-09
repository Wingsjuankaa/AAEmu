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
            // x2game FUN_39a502f0 uses the serializer's ReadBytes/WriteBytes
            // pair. The UInt16 length belongs to that byte-array contract;
            // the following bytes are the fixed AA8 internal detail union.
            stream.Write((ushort)128);
            _item.WriteUpdateDetailBlock(stream);
            return stream;
        }
    }
}
