using AAEmu.Game.Models.Game.Quests.Templates;

#pragma warning disable IDE0130 // Namespace does not match folder structure

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// Only used in one instance of a test quest
/// </summary>
/// <param name="parentComponent"></param>
public class QuestActObjItemGroupUse(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public override bool CountsAsAnObjective => true;
    public uint ItemGroupId { get; set; }
    public uint HighlightDoodadId { get; set; }
    public int HighlightDoodadPhase { get; set; }
    public bool UseAlias { get; set; }
    public uint QuestActObjAliasId { get; set; }
    public bool DropWhenDestroy { get; set; }
    public bool DestroyWhenDrop { get; set; }
    public bool CheckExist { get; set; }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) => currentObjectiveCount >= Math.Max(1, Count);

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        quest.Owner.Events.OnItemGroupUse += questAct.OnItemGroupUse;
    }

    public override void FinalizeAction(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnItemGroupUse -= questAct.OnItemGroupUse;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnItemGroupUse(QuestAct questAct, object sender, AAEmu.Game.Models.Game.Units.OnItemGroupUseArgs args)
    {
        if (questAct.Id == ActId && args.ItemGroupId == ItemGroupId && args.Count > 0)
            AddObjective(questAct, args.Count);
    }
}
