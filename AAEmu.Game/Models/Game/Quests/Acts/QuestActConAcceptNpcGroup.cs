using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActConAcceptNpcGroup : QuestActTemplate
    {
        public uint QuestMonsterGroupId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            var target = quest.InteractionTarget ?? character.CurrentTarget;
            var npcTemplateId = Quest.ResolveNpcGroupTargetTemplateId(
                target,
                QuestMonsterGroupId);
            if (npcTemplateId == 0)
                return false;

            quest.QuestAcceptorType = QuestAcceptorType.Npc;
            quest.AcceptorType = npcTemplateId;
            return true;
        }
    }
}
