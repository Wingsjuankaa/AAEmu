using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConReportNpcGroup(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public uint QuestMonsterGroupId { get; set; }
    public bool UseAlias { get; set; }
    public uint QuestActObjAliasId { get; set; }

    public static bool MatchesNpc(uint groupId, uint npcId, Func<uint, uint, bool> groupContainsNpc)
    {
        return groupId != 0 && npcId != 0 && groupContainsNpc(groupId, npcId);
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        var targetNpcId = quest.Owner.CurrentTarget is Npc npc ? npc.TemplateId : 0;
        return questAct.OverrideObjectiveCompleted ||
               MatchesNpc(QuestMonsterGroupId, targetNpcId, QuestManager.Instance.CheckGroupNpc);
    }

    public override void InitializeQuest(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        quest.Owner.Events.OnReportNpc += questAct.OnReportNpc;
    }

    public override void FinalizeQuest(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnReportNpc -= questAct.OnReportNpc;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnReportNpc(QuestAct questAct, object sender, OnReportNpcArgs args)
    {
        if (questAct.Id != ActId ||
            !MatchesNpc(QuestMonsterGroupId, args.NpcId, QuestManager.Instance.CheckGroupNpc))
            return;

        var quest = questAct.QuestComponent.Parent.Parent;
        var minimumProgress = quest.Template.LetItDone
            ? QuestObjectiveStatus.CanEarlyComplete
            : QuestObjectiveStatus.QuestComplete;
        if (quest.GetQuestObjectiveStatus() < minimumProgress)
            return;

        quest.SelectedRewardIndex = args.Selected;
        questAct.OverrideObjectiveCompleted = true;
        if (quest.Step <= QuestComponentKind.Progress)
            quest.Step = QuestComponentKind.Ready;
        questAct.RequestEvaluation();
    }
}
