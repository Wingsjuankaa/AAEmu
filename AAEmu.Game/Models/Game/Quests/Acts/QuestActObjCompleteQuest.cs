using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActObjCompleteQuest(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public override bool CountsAsAnObjective => true;
    public uint QuestId { get; set; }
    public bool AcceptWith { get; set; }
    public bool UseAlias { get; set; }
    public uint QuestActObjAliasId { get; set; }

    /// <summary>
    /// Checks if a specific quest has been completed before
    /// </summary>
    /// <param name="quest"></param>
    /// <param name="questAct"></param>
    /// <param name="currentObjectiveCount"></param>
    /// <returns></returns>
    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        return currentObjectiveCount >= Math.Max(1, Count);
    }

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        if (AcceptWith && quest.Owner.Quests.HasQuestCompleted(QuestId))
            SetObjective(quest, Math.Max(1, GetObjective(quest)));
        quest.Owner.Events.OnQuestComplete += questAct.OnQuestComplete;
    }

    public override void FinalizeAction(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnQuestComplete -= questAct.OnQuestComplete;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnQuestComplete(QuestAct questAct, object sender, OnQuestCompleteArgs args)
    {
        if (questAct.Id == ActId && args.QuestId == QuestId)
            AddObjective(questAct, 1);
    }
}
