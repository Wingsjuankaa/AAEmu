using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConAcceptComponent(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public uint QuestContextId { get; set; }

    public static bool MatchesContextReference(
        uint activeQuestId,
        uint referencedQuestId,
        bool referencedQuestExists)
    {
        if (activeQuestId == 0 || referencedQuestId == 0)
            return false;

        // AA10 has 299 self references used by component/event starters and 176
        // cross-quest links. Every enabled cross-reference resolves to a native
        // quest_context row; it is a provenance link, not an instruction to add
        // another quest as a side effect.
        return referencedQuestId == activeQuestId || referencedQuestExists;
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        var referencedQuestExists = AAEmu.Game.Core.Managers.QuestManager.Instance.GetTemplate(QuestContextId) != null;
        var valid = MatchesContextReference(quest.TemplateId, QuestContextId, referencedQuestExists);
        if (!valid)
            Logger.Warn($"{QuestActTemplateName}({DetailId}): invalid context reference from quest {quest.TemplateId} to {QuestContextId}");

        return valid;
    }
}
