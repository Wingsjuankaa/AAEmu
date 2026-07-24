using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCSkillEndedPacket : GamePacket
    {
        private readonly bool _completed;

        /// <summary>
        /// Kakao 8.0 r558734 reads opcode 0x345 as one Boolean. It does not
        /// carry the historical skill transaction id.
        /// </summary>
        public SCSkillEndedPacket(bool completed = true) : base(SCOffsets.SCSkillEndedPacket, 5)
        {
            _completed = completed;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_completed);
            return stream;
        }

        public override string Verbose()
        {
            return $" - completed={_completed}";
        }
    }
}
