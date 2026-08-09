using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class AAPointUpdate : ItemTask
    {
        private readonly long _amount;

        public AAPointUpdate(long amount)
        {
            _type = ItemAction.ChangeAaPoint; // 17 in the 8.0 protocol
            _amount = amount;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(_amount);
            return stream;
        }
    }
}
