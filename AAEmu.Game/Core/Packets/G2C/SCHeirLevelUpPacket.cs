using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Exact AA8 ancestral level-up notification: one unit object-id BC.
    /// </summary>
    public sealed class SCHeirLevelUpPacket : GamePacket
    {
        private readonly uint _objId;

        public SCHeirLevelUpPacket(uint objId) : base(SCOffsets.SCHeirLevelUpPacket, 5)
        {
            _objId = objId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            return stream;
        }
    }
}
