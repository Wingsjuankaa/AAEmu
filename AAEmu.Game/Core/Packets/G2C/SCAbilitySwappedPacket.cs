using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCAbilitySwappedPacket : GamePacket
    {
        private readonly uint _objId;
        private readonly AbilityType _oldAbility;
        private readonly AbilityType _newAbility;

        public SCAbilitySwappedPacket(
            uint objId,
            AbilityType oldAbility,
            AbilityType newAbility) : base(SCOffsets.SCAbilitySwappedPacket, 5)
        {
            _objId = objId;
            _oldAbility = oldAbility;
            _newAbility = newAbility;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write((byte)_oldAbility);
            stream.Write((byte)_newAbility);

            // AA8 serializes three old/new entries, but its handler treats them as a
            // terminated change list. A simple swap must contain one valid pair. If two
            // or more new entries are valid, the client takes the bulk-replacement path
            // and intentionally omits the ABILITY_CHANGED UI event.
            stream.Write((byte)AbilityType.None);
            stream.Write((byte)AbilityType.None);
            stream.Write((byte)AbilityType.None);
            stream.Write((byte)AbilityType.None);
            return stream;
        }
    }
}
