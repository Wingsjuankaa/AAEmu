using AAEmu.Game.Models.Game.Quests.Templates;

#pragma warning disable IDE0130 // Namespace does not match folder structure

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// No longer used?
/// </summary>
/// <param name="parentComponent"></param>
public class QuestActObjCondition(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override AAEmu.Game.Models.Game.Units.QuestObjectiveEventType EventType => AAEmu.Game.Models.Game.Units.QuestObjectiveEventType.QuestCondition;
    public uint ConditionId { get; set; }
    public uint QuestContextId { get; set; }

    protected override bool Matches(QuestAct questAct, AAEmu.Game.Models.Game.Units.OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && args.QuestId == QuestContextId && args.Rank == ConditionId;
}
