using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

/// <summary>
/// Native client-local doodad phase transition driven by one character's quest state.
/// The shared server doodad must not execute this as a world phase mutation; interaction
/// routing resolves these transitions per character in <see cref="Doodad"/>.
/// </summary>
public class DoodadFuncQuestReact : DoodadPhaseFuncTemplate
{
    public uint QuestId { get; set; }
    public QuestStatus QuestStatus { get; set; }
    public uint QuestStatusId { get => (uint)QuestStatus; set => QuestStatus = (QuestStatus)value; }
    public int NextPhase { get; set; }
    public uint QuestComponentId { get; set; }
    public bool BubbleOnce { get; set; }
    public uint BubbleId { get; set; }

    public bool Matches(QuestStatus status, uint componentId)
        => status == QuestStatus && (QuestComponentId == 0 || QuestComponentId == componentId);

    public override bool Use(BaseUnit caster, Doodad owner)
    {
        if (caster is not Character character || owner == null)
            return false;

        if (!TryResolveViewerNext(character, owner.FuncGroupId, out var viewerPhase))
            return false;

        if (DoodadQuestReactRules.ShouldMutateSharedPhase())
        {
            owner.OverridePhase = (int)viewerPhase;
            return true;
        }

        owner.SetQuestReactViewerPhase(character.ObjId, viewerPhase);
        return false;
    }

    public bool TryResolveViewerNext(Character character, uint currentPhase, out uint viewerPhase)
    {
        viewerPhase = currentPhase;
        if (character == null || QuestId == 0)
            return false;

        ReadQuestState(character, QuestId, QuestComponentId, out var actualStatus, out var activeComponentId,
            out var readyStepContainsRequiredComponent);

        if (!DoodadQuestReactRules.MatchesStatus(QuestStatusId, actualStatus) ||
            !DoodadQuestReactRules.MatchesComponent(QuestComponentId, activeComponentId, readyStepContainsRequiredComponent))
        {
            return false;
        }

        var next = DoodadQuestReactRules.NextViewerPhase(currentPhase, NextPhase);
        if (!DoodadQuestReactRules.ShouldKeepViewerPhase(currentPhase, next))
            return false;
        viewerPhase = next;
        return true;
    }

    private static void ReadQuestState(
        Character character,
        uint questId,
        uint requiredComponentId,
        out QuestStatus actualStatus,
        out uint activeComponentId,
        out bool readyStepContainsRequiredComponent)
    {
        readyStepContainsRequiredComponent = false;
        activeComponentId = 0;

        if (character.Quests.ActiveQuests.TryGetValue(questId, out var quest))
        {
            actualStatus = quest.Status;
            activeComponentId = quest.CurrentComponentId != 0 ? quest.CurrentComponentId : quest.ComponentId;
            readyStepContainsRequiredComponent = requiredComponentId != 0 &&
                                                 actualStatus == QuestStatus.Ready &&
                                                 quest.Step == QuestComponentKind.Ready &&
                                                 quest.CurrentStep?.Components.ContainsKey(requiredComponentId) == true;
            return;
        }

        actualStatus = character.Quests.HasQuestCompleted(questId)
            ? QuestStatus.Completed
            : QuestStatus.Invalid;
    }
}
