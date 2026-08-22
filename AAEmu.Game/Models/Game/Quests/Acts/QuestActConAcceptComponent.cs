using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConAcceptComponent(QuestComponentTemplate parentComponent)
    : QuestActTemplate(parentComponent), IQuestRewardPreflight
{
    public uint QuestContextId { get; set; }

    public static bool IsValidContextReference(
        uint sourceQuestId,
        uint referencedQuestId) =>
        sourceQuestId != 0 && referencedQuestId != 0;

    public static bool ShouldStartSuccessor(
        uint sourceQuestId,
        uint referencedQuestId,
        bool referencedQuestAccepted,
        bool referencedQuestCompleted) =>
        IsValidContextReference(sourceQuestId, referencedQuestId) &&
        referencedQuestId != sourceQuestId &&
        !referencedQuestAccepted &&
        !referencedQuestCompleted;

    public static bool ResolveContextReference(
        uint sourceQuestId,
        uint referencedQuestId,
        bool referencedQuestAccepted,
        bool referencedQuestCompleted,
        Func<uint, bool> startSuccessor)
    {
        if (!IsValidContextReference(sourceQuestId, referencedQuestId))
            return false;
        if (!ShouldStartSuccessor(
                sourceQuestId,
                referencedQuestId,
                referencedQuestAccepted,
                referencedQuestCompleted))
            return true;

        return startSuccessor(referencedQuestId);
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        if (!IsValidContextReference(quest.TemplateId, QuestContextId))
        {
            Logger.Warn($"{QuestActTemplateName}({DetailId}): invalid context reference from quest {quest.TemplateId} to {QuestContextId}");
            return false;
        }

        // All 299 AA10 self references live in Start components. They identify
        // a quest accepted by another quest component; Start acts are OR checks,
        // so an NPC starter can remain as the native recovery path.
        // All 175 AA10 cross references live in Reward components and point to
        // the successor context. Materialize it exactly once before the source
        // reward completes. The wire has no Component acceptor kind, so preserve
        // the referenced context identity in AcceptorId with type Unknown.
        var resolved = ResolveContextReference(
            quest.TemplateId,
            QuestContextId,
            quest.Owner.Quests.HasQuest(QuestContextId),
            quest.Owner.Quests.HasQuestCompleted(QuestContextId),
            successorId => quest.Owner.Quests.AddQuest(
                successorId,
                false,
                QuestAcceptorType.Unknown,
                successorId));
        if (!resolved)
            Logger.Warn($"{QuestActTemplateName}({DetailId}): quest {quest.TemplateId} failed to start successor {QuestContextId}");

        return resolved;
    }

    public bool CanApplyReward(Quest quest, QuestAct questAct)
    {
        if (!IsValidContextReference(quest.TemplateId, QuestContextId))
            return false;
        if (QuestContextId == quest.TemplateId ||
            quest.Owner.Quests.HasQuest(QuestContextId) ||
            quest.Owner.Quests.HasQuestCompleted(QuestContextId))
            return true;

        if (quest.Owner is not Character owner)
            return false;

        var successor = QuestManager.Instance.GetTemplate(QuestContextId);
        if (successor == null || !successor.MeetsContextRequirements(owner))
            return false;

        return successor.GetComponents(QuestComponentKind.Start).All(component =>
            UnitRequirementsGameData.Instance.CanComponentRun(component, owner));
    }
}
