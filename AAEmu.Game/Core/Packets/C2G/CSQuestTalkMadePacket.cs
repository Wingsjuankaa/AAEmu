using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSQuestTalkMadePacket : GamePacket
    {
        public CSQuestTalkMadePacket() : base(CSOffsets.CSQuestTalkMadePacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var objId = stream.ReadBc();
            var questContextId = stream.ReadUInt32();
            var questComponentId = stream.ReadUInt32();
            var questActId = stream.ReadUInt32();

            _log.Debug(
                "[AA8QuestTalk] character={0}, npcObjId={1}, quest={2}, component={3}, act={4}",
                Connection.ActiveChar?.Name ?? "<none>",
                objId,
                questContextId,
                questComponentId,
                questActId);

            Connection.ActiveChar?.Quests?.OnTalkMade(
                objId,
                questContextId,
                questComponentId,
                questActId);
        }
    }
}
