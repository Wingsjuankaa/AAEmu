using AAEmu.Commons.Network;
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
            var objId = stream.ReadBc();
            var bc = stream.ReadBc();
            var selected = stream.ReadInt32();

            var target = objId > 0 ? WorldManager.Instance.GetGameObject(objId) : null;
            var targetTemplateId = target switch
            {
                Doodad doodad => (uint)doodad.TemplateId,
                Npc npc => (uint)npc.TemplateId,
                _ => 0u
            };
            _log.Info(
                "[AA8QuestComplete] character={0}, quest={1}, objId={2}, targetType={3}, " +
                "targetTemplate={4}, bc={5}, selected={6}",
                Connection.ActiveChar.Name, questId, objId,
                target?.GetType().Name ?? "<none>", targetTemplateId, bc, selected);

            if (objId > 0 &&
                Connection.ActiveChar.CurrentTarget != null &&
                Connection.ActiveChar.CurrentTarget.ObjId != objId)
                return;
            Connection.ActiveChar.Quests.Complete(questId, selected);
        }
    }
}
