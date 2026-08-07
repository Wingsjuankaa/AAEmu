using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCSpecialAbilityActivedPacket : GamePacket
    {
        private readonly byte _activeAbility;

        public SCSpecialAbilityActivedPacket(AbilityType activeAbility)
            : base(SCOffsets.SCSpecialAbilityActivedPacket, 5)
        {
            _activeAbility = (byte)activeAbility;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_activeAbility);
            return stream;
        }
    }
}
