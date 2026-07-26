using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActConAcceptNpcGroup : QuestActTemplate
    {
        public uint QuestMonsterGroupId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            if (!(character.CurrentTarget is Npc npc))
                return false;
            if (!QuestManager.Instance.CheckGroupNpc(
                    QuestMonsterGroupId,
                    npc.TemplateId))
                return false;

            quest.QuestAcceptorType = QuestAcceptorType.Npc;
            quest.AcceptorType = npc.TemplateId;
            return true;
        }
    }
}
