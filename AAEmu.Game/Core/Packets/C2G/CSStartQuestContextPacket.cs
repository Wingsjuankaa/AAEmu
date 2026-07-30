using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSStartQuestContextPacket : GamePacket
    {
        public CSStartQuestContextPacket() : base(CSOffsets.CSStartQuestContextPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var questId = stream.ReadUInt32();
            var objId = stream.ReadBc();
            var objId2 = stream.ReadBc();
            var type = stream.ReadUInt32();

            using var observation =
                AA8ObservationService.Instance.BeginInteraction(
                    Connection.ActiveChar,
                    "quest_start",
                    questId,
                    $"{{\"obj_id\":{objId},\"obj_id_2\":{objId2},\"type\":{type}}}");
            if (!observation.Allowed)
                return;
            AA8ObservationService.Instance.RecordEvent(
                Connection.ActiveChar,
                "request",
                "attempted",
                "CSStartQuestContext",
                questId,
                actualJson:
                    $"{{\"obj_id\":{objId},\"obj_id_2\":{objId2},\"type\":{type}}}");
            if (objId > 0 &&
                Connection.ActiveChar.CurrentTarget != null &&
                Connection.ActiveChar.CurrentTarget.ObjId != objId)
            {
                AA8ObservationService.Instance.RecordEvent(
                    Connection.ActiveChar,
                    "request",
                    "blocked",
                    "CSStartQuestContext",
                    questId,
                    blockerCode: "interaction_target_mismatch");
                observation.SetOutcome("blocked_target");
                return;
            }
            Connection.ActiveChar.Quests.Add(
                questId,
                Connection.ActiveChar.CurrentTarget);
        }
    }
}
