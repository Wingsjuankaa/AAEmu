using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSStartInteractionPacket : GamePacket
    {
        public CSStartInteractionPacket() : base(CSOffsets.CSStartInteractionPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var npcObjId = stream.ReadBc();
            var objId = stream.ReadBc();
            var extraInfo = stream.ReadInt32();
            var pickId = stream.ReadInt32();
            var mouseButton = stream.ReadByte();
            var modifierKeys = stream.ReadInt32();

            _log.Debug(
                "StartInteraction, NpcObjId: {0}, ObjId: {1}, ExtraInfo: {2}, PickId: {3}, Mouse: {4}, Modifiers: {5}",
                npcObjId,
                objId,
                extraInfo,
                pickId,
                mouseButton,
                modifierKeys);

            var npc = WorldManager.Instance.GetNpc(npcObjId);
            if (npc == null)
            {
                _log.Warn("StartInteraction ignored: NPC object {0} was not found", npcObjId);
                return;
            }

            var readyReportQuests = Connection.ActiveChar.Quests.Quests.Values
                .Where(quest => quest.Status == QuestStatus.Ready)
                .Where(quest => quest.Template.GetComponents(QuestComponentKind.Ready)
                    .SelectMany(component => QuestManager.Instance.GetActs(component.Id))
                    .Where(act => act.DetailType == "QuestActConReportNpc")
                    .Select(act => act.GetTemplate<QuestActConReportNpc>())
                    .Any(report => report != null && report.NpcId == npc.TemplateId))
                .Select(quest => quest.TemplateId)
                .OrderBy(questId => questId)
                .ToArray();

            _log.Info(
                "[QuestNpcProbe] character={0} npcObj={1} npcTemplate={2} readyReportQuests={3}",
                Connection.ActiveChar.Name,
                npc.ObjId,
                npc.TemplateId,
                readyReportQuests.Length == 0
                    ? "<none>"
                    : string.Join(",", readyReportQuests));

            // AA8 expects a response to the initial right-click/F interaction.
            // For quest NPCs the native default is skill 0: the client then
            // selects the first locally calculated interaction, which includes
            // the NPC quest context.  Without this response the interaction
            // stops here and CSInteractNPC is never emitted.
            uint option = 0;
            if (npc.Template.Banker)
                option = SkillsEnum.UseWarehouse;
            else if (npc.Template.AbilityChanger)
                option = SkillsEnum.ChangeSkillsets;
            else if (npc.Template.Auctioneer)
                option = SkillsEnum.UseAuctioneer;
            else if (npc.Template.Priest)
                option = SkillsEnum.Blessing;
            else if (npc.Template.Repairman)
                option = SkillsEnum.Repair;
            else if (npc.Template.Merchant)
                option = SkillsEnum.UseStore;
            else if (npc.Template.Stabler)
                option = SkillsEnum.HealPetSWounds;
            else if (npc.Template.Expedition)
                option = SkillsEnum.FormGuild;
            else if (npc.Template.RecrutingBattlefieldId > 0)
                option = SkillsEnum.WarSupport;
            else if (npc.Template.Blacksmith)
                option = SkillsEnum.ItemFusion;

            Connection.ActiveChar.SendPacket(
                new SCNpcInteractionSkillListPacket(
                    npcObjId,
                    objId,
                    extraInfo,
                    pickId,
                    mouseButton,
                    modifierKeys,
                    new[] { option }));
        }
    }
}
