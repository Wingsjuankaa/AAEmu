using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.NPChar;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSCompleteQuestContextPacket : GamePacket
    {
        public CSCompleteQuestContextPacket() : base(CSOffsets.CSCompleteQuestContextPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var questId = stream.ReadUInt32();
            var npcObjId = stream.ReadBc();
            var doodadObjId = stream.ReadBc();
            var selected = stream.ReadInt32();

            using var observation =
                AA8ObservationService.Instance.BeginInteraction(
                    Connection.ActiveChar,
                    "quest_complete",
                    questId,
                    $"{{\"npc_obj_id\":{npcObjId},\"doodad_obj_id\":{doodadObjId},\"selected\":{selected}}}");
            if (!observation.Allowed)
                return;
            AA8ObservationService.Instance.RecordEvent(
                Connection.ActiveChar,
                "request",
                "attempted",
                "CSCompleteQuestContext",
                questId,
                actualJson:
                    $"{{\"npc_obj_id\":{npcObjId},\"doodad_obj_id\":{doodadObjId},\"selected\":{selected}}}");
            var targetObjId = npcObjId != 0 ? npcObjId : doodadObjId;
            var target = targetObjId > 0
                ? WorldManager.Instance.GetGameObject(targetObjId)
                : null;
            var targetTemplateId = target switch
            {
                Doodad doodad => (uint)doodad.TemplateId,
                Npc npc => (uint)npc.TemplateId,
                _ => 0u
            };
            _log.Info(
                "[AA8QuestComplete] character={0}, quest={1}, npcObjId={2}, doodadObjId={3}, " +
                "targetType={4}, targetTemplate={5}, selected={6}",
                Connection.ActiveChar.Name, questId, npcObjId, doodadObjId,
                target?.GetType().Name ?? "<none>", targetTemplateId, selected);

            if (targetObjId > 0 &&
                Connection.ActiveChar.CurrentTarget != null &&
                Connection.ActiveChar.CurrentTarget.ObjId != targetObjId)
            {
                AA8ObservationService.Instance.RecordEvent(
                    Connection.ActiveChar,
                    "request",
                    "blocked",
                    "CSCompleteQuestContext",
                    questId,
                    blockerCode: "interaction_target_mismatch");
                observation.SetOutcome("blocked_target");
                return;
            }

            if (doodadObjId != 0)
            {
                Connection.ActiveChar.Quests.OnReportToDoodad(
                    doodadObjId,
                    questId,
                    selected);
                return;
            }

            if (npcObjId != 0)
            {
                Connection.ActiveChar.Quests.OnReportToNpc(
                    npcObjId,
                    questId,
                    selected);
                return;
            }

            // Hidden/journal completion legitimately has no world target.
            Connection.ActiveChar.Quests.Complete(questId, selected);
        }
    }
}
