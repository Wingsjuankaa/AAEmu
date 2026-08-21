using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// Checks if a item has been obtained since the quest was started (does not require the item in the inventory)
/// </summary>
/// <param name="parentComponent"></param>
public class QuestActEtcItemObtain(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public override bool CountsAsAnObjective => true;
    public uint ItemId { get; set; }
    public uint HighlightDoodadId { get; set; }
    public bool Cleanup { get; set; }

    /// <summary>
    /// Checks if the Objective count has been met
    /// </summary>
    /// <param name="quest"></param>
    /// <param name="questAct"></param>
    /// <param name="currentObjectiveCount"></param>
    /// <returns></returns>
    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        Logger.Debug($"{QuestActTemplateName}({DetailId}).RunAct: Quest: {quest.TemplateId}, Owner {quest.Owner.Name} ({quest.Owner.Id}), ItemId {ItemId}, Count {currentObjectiveCount}/{Count}");
        return IsCompleted(currentObjectiveCount, Count, quest.Template.Score);
    }

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        quest.Owner.Events.OnItemGather += questAct.OnItemGather;
    }

    public override void FinalizeAction(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnItemGather -= questAct.OnItemGather;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnItemGather(QuestAct questAct, object sender, OnItemGatherArgs e)
    {
        // This act records acquisitions made after quest acceptance. Unlike ObjItemGather,
        // later consumption/removal must not reduce the accumulated objective.
        if (MatchesAcquisition(questAct.Id, ActId, e.ItemId, ItemId, e.Count))
            AddObjective(questAct, e.Count);
    }

    internal static bool MatchesAcquisition(uint questActId, uint templateActId, uint acquiredItemId,
        uint requiredItemId, int acquiredCount) =>
        questActId == templateActId && acquiredItemId == requiredItemId && acquiredCount > 0;

    internal static bool IsCompleted(int currentObjectiveCount, int count, int score) =>
        score > 0 ? currentObjectiveCount * count >= score : currentObjectiveCount >= count;

    public override void QuestCleanup(Quest quest)
    {
        base.QuestCleanup(quest);
        if (!Cleanup)
            return;

        quest.Owner?.Inventory.ConsumeItem(null, ItemTaskType.QuestRemoveSupplies, ItemId, Count, null);
    }
}
