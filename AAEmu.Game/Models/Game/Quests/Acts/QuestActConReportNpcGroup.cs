using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    /// <summary>
    /// Native report endpoint that accepts any NPC in a quest monster group.
    /// </summary>
    public class QuestActConReportNpcGroup : QuestActTemplate
    {
        public uint QuestMonsterGroupId { get; set; }
        public bool UseAlias { get; set; }
        public uint QuestActObjAliasId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            var target = quest.InteractionTarget ?? character.CurrentTarget;
            return Quest.MatchesNpcGroupTarget(target, QuestMonsterGroupId);
        }
    }
}
