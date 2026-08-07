using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCGamePointInitedPacket : GamePacket
    {
        private readonly byte _kind;
        private readonly uint _point;

        public SCGamePointInitedPacket(byte kind, uint point) : base(SCOffsets.SCGamePointInitedPacket, 5)
        {
            _kind = kind;
            _point = point;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_kind);
            stream.Write(_point);
            return stream;
        }
    }
}
