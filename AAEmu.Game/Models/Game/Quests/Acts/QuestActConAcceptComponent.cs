using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Core.Managers;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActConAcceptComponent : QuestActTemplate
    {
        public uint QuestContextId { get; set; }

        public static bool MatchesContextReference(
            uint activeQuestId,
            uint referencedQuestId,
            bool referencedQuestExists)
        {
            if (activeQuestId == 0 || referencedQuestId == 0)
                return false;

            // A self-reference is the native marker for quests started by a
            // component/event rather than an NPC, item, doodad or sphere.
            // Cross-quest references are successor links and are valid only
            // when the referenced quest is actually materialized.
            return referencedQuestId == activeQuestId || referencedQuestExists;
        }

        public override bool Use(Character character, Quest quest, int objective)
        {
            var referencedQuestExists =
                QuestManager.Instance.GetTemplate(QuestContextId) != null;
            var valid = MatchesContextReference(
                quest?.TemplateId ?? 0,
                QuestContextId,
                referencedQuestExists);
            if (!valid)
            {
                _log.Warn(
                    "[AA8QuestComponentAccept] Invalid context reference: " +
                    "quest={0}, referencedQuest={1}, materialized={2}",
                    quest?.TemplateId ?? 0,
                    QuestContextId,
                    referencedQuestExists);
                return false;
            }

            // There is no AA8 protocol acceptor kind for a component. Keep
            // the wire-visible kind Unknown and preserve the exact native
            // quest-context identity in AcceptorType.
            quest.AcceptorType = QuestContextId;
            _log.Debug(
                "[AA8QuestComponentAccept] Valid context reference: " +
                "quest={0}, referencedQuest={1}",
                quest.TemplateId,
                QuestContextId);
            return true;
        }
    }
}
