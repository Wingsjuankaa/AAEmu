using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCSkillEndedPacket : GamePacket
    {
        private readonly ushort _tlId;

        /// <summary>
        /// Kakao 8.0 r558734 routes opcode 0x345 to the incoming skill-end
        /// handler, which removes the active client skill transaction by id.
        /// The similarly numbered Boolean reader belongs to the opposite
        /// protocol direction and is not the SC payload used here.
        /// </summary>
        public SCSkillEndedPacket(ushort tlId) : base(SCOffsets.SCSkillEndedPacket, 5)
        {
            _tlId = tlId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_tlId);
            return stream;
        }

        public override string Verbose()
        {
            return $" - tl={_tlId}";
        }
    }
}
