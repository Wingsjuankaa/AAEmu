using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class ItemRemoveCrafting : ItemTask
    {
        private readonly ulong _id;

        public ItemRemoveCrafting(ulong id)
        {
            _id = id;
            _type = ItemAction.RemoveCrafting; // 13 in the 8.0 protocol
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(_id);
            return stream;
        }
    }
}
