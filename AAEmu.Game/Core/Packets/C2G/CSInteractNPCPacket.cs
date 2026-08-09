using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSInteractNPCPacket : GamePacket
    {
        public CSInteractNPCPacket() : base(CSOffsets.CSInteractNpcPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var objId = stream.ReadBc();
            var isTargetChanged = stream.ReadBoolean();

            _log.Debug("InteractNPC, BcId: {0}", objId);

            // AA8 r558734 acknowledges NPC interaction in the ordered DD05
            // stream. Ordinary combat aggro updates remain level 1.
            Connection.SendPacket(SCUnitAiAggroPacket.CreateInteractionClear(objId));
        }
    }
}
