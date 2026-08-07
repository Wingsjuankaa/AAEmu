using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G
{
    /// <summary>
    /// Exact AA8 ancestral level-up request. The level-5 packet has no body.
    /// </summary>
    public sealed class CSHeirLevelUpPacket : GamePacket
    {
        public CSHeirLevelUpPacket() : base(CSOffsets.CSHeirLevelUpPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            Connection.ActiveChar?.TryLevelUpHeir();
        }
    }
}
