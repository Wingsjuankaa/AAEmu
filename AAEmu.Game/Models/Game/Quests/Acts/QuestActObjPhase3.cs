using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>Shared event lifecycle for server-authoritative Phase 3 counters.</summary>
public abstract class QuestActObjPhase3Event(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    protected abstract QuestObjectiveEventType EventType { get; }

    public override bool CountsAsAnObjective => true;
    public bool UseAlias { get; set; }
    public uint QuestActObjAliasId { get; set; }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) =>
        currentObjectiveCount >= Math.Max(1, Count);

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        quest.Owner.Events.OnQuestObjective += questAct.OnQuestObjective;
    }

    public override void FinalizeAction(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnQuestObjective -= questAct.OnQuestObjective;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnQuestObjective(QuestAct questAct, object sender, OnQuestObjectiveArgs args)
    {
        if (questAct.Id != ActId || args.Type != EventType || args.Amount <= 0 || !Matches(questAct, args))
            return;

        AddObjective(questAct, args.Amount);
    }

    protected virtual bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        args.Actor?.Id == questAct.QuestComponent.Parent.Parent.Owner.Id;
}

public sealed class QuestActObjGainExpPoint(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.GainExpPoint;
}

public sealed class QuestActObjGainHonorPoint(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.GainHonorPoint;
}

public sealed class QuestActObjGainLivingPoint(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.GainLivingPoint;
}

public sealed class QuestActObjConsumeEvolvingMaterial(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.ConsumeEvolvingMaterial;
}

public sealed class QuestActObjEnchantScaleCount(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.EnchantScaleCount;
}

public sealed class QuestActObjMonsterContrHunt(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.MonsterContribution;
    public uint NpcId { get; set; }
    public uint HighlightDoodadId { get; set; }
    public int HighlightDoodadPhase { get; set; }
    public bool LongDist { get; set; }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && args.NpcId == NpcId;
}

public sealed class QuestActObjMonsterContrGroupHunt(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.MonsterContribution;
    public uint QuestMonsterGroupId { get; set; }
    public uint HighlightDoodadId { get; set; }
    public int HighlightDoodadPhase { get; set; }
    public bool LongDist { get; set; }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && QuestManager.Instance.CheckGroupNpc(QuestMonsterGroupId, args.NpcId);
}

public sealed class QuestActObjNpcKill(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.NpcKill;
    public int LevelMin { get; set; }
    public int LevelMax { get; set; }
    public int HeirLevelMin { get; set; }
    public int HeirLevelMax { get; set; }
    public int GradeBitFlag { get; set; }
    public bool LongDist { get; set; }
    public bool TeamShare { get; set; }
    public bool IsParty { get; set; }

    public static bool MatchesVictim(int level, int heirLevel, int gradeId, int levelMin, int levelMax,
        int heirLevelMin, int heirLevelMax, int gradeBitFlag)
    {
        if (level < levelMin || (levelMax > 0 && level > levelMax) ||
            heirLevel < heirLevelMin || (heirLevelMax > 0 && heirLevel > heirLevelMax))
            return false;

        return gradeId is > 0 and <= 32 && (gradeBitFlag & (1 << (gradeId - 1))) != 0;
    }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && MatchesVictim(args.Level, args.HeirLevel, args.GradeId,
            LevelMin, LevelMax, HeirLevelMin, HeirLevelMax, GradeBitFlag);
}

public sealed class QuestActObjPcKill(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.PcKill;
    public int LevelGap { get; set; }
    public bool TeamShare { get; set; }
    public bool IsParty { get; set; }

    public static bool MatchesLevelGap(int killerLevel, int victimLevel, int levelGap) =>
        victimLevel + Math.Max(0, levelGap) >= killerLevel;

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args)
    {
        var owner = questAct.QuestComponent.Parent.Parent.Owner;
        return (args.Actor?.Id == owner.Id || TeamShare) && MatchesLevelGap(owner.Level, args.Level, LevelGap);
    }
}

public sealed class QuestActObjInviteTeamFaction(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.InviteTeamFaction;
    public uint QuestActObjInviteId { get; set; }
    public uint BuffId { get; set; }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && QuestActObjInviteId == 1 && args.BuffId == BuffId;
}

public sealed class QuestActObjSellBackpackGood(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.SellBackpackGood;
    public uint ContentItemId { get; set; }
    public string ContentItemType { get; set; } = string.Empty;
    public uint QuestMonsterGroupId { get; set; }

    public static bool MatchesContent(string contentType, uint contentId, uint itemId,
        Func<uint, IReadOnlySet<uint>> tagResolver) =>
        contentType == "Item" ? itemId == contentId :
        contentType == "Tag" && tagResolver(contentId).Contains(itemId);

    public bool MatchesSale(uint itemId, uint outletNpcId)
    {
        var itemMatches = MatchesContent(ContentItemType, ContentItemId, itemId,
            tagId => TagsGameData.Instance.GetIdsByTagId(TagsGameData.TagType.Items, tagId));
        return itemMatches && (QuestMonsterGroupId == 0 || QuestManager.Instance.CheckGroupNpc(QuestMonsterGroupId, outletNpcId));
    }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && MatchesSale(args.ItemId, args.NpcId);
}

public sealed class QuestActObjFactionCompetition(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.FactionCompetition;
    public uint ZoneGroupId { get; set; }
    public int CompleteRank { get; set; }
    public bool UseResult { get; set; }

    public static int EncodeRank(int completeRank, int actualRank) =>
        actualRank > 0 && actualRank <= completeRank ? completeRank - actualRank + 1 : 0;

    public static int DecodeRank(int completeRank, int encodedRank) =>
        encodedRank > 0 && encodedRank <= completeRank ? completeRank - encodedRank + 1 : 0;

    public override int MaxObjective() => Math.Max(1, CompleteRank);

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) => currentObjectiveCount > 0;

    public override void OnQuestObjective(QuestAct questAct, object sender, OnQuestObjectiveArgs args)
    {
        if (questAct.Id != ActId || args.Type != EventType || !Matches(questAct, args))
            return;

        // Persist the exact rank in the existing AA10 objective slot. Lower ranks are better,
        // so encode them in the positive objective domain used by quest completion.
        SetObjective(questAct, EncodeRank(CompleteRank, args.Rank));
    }

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        // A live-rank objective accepted mid-competition must see the current snapshot even
        // when no later score mutation occurs. Result-only objectives still reject this event.
        if (!UseResult && quest.Owner is Character character)
            WorldIntegration.SyncFactionCompetitionToCharacter?.Invoke(character);
    }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && args.ZoneGroupId == ZoneGroupId && args.Rank > 0 &&
        CompleteRank > 0 && args.Rank <= CompleteRank && (!UseResult || args.Result);
}

public sealed class QuestActObjConquestWar(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override QuestObjectiveEventType EventType => QuestObjectiveEventType.ConquestWar;
    public uint ZoneGroupId { get; set; }
    public int CompleteRank { get; set; }

    public override int MaxObjective() => Math.Max(1, CompleteRank);

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) => currentObjectiveCount > 0;

    public override void OnQuestObjective(QuestAct questAct, object sender, OnQuestObjectiveArgs args)
    {
        if (questAct.Id != ActId || args.Type != EventType || !Matches(questAct, args))
            return;

        SetObjective(questAct, QuestActObjFactionCompetition.EncodeRank(CompleteRank, args.Rank));
    }

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        // Conquest objectives are authored without a result-only flag. A quest accepted while
        // TowerDef 126 is already active must consume the current faction rank immediately.
        if (quest.Owner is Character character)
            WorldIntegration.SyncFactionCompetitionToCharacter?.Invoke(character);
    }

    protected override bool Matches(QuestAct questAct, OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && args.ZoneGroupId == ZoneGroupId && args.Rank > 0 &&
        CompleteRank > 0 && args.Rank <= CompleteRank;
}

public sealed class QuestActObjCompleteQuestGroup(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public override bool CountsAsAnObjective => true;
    public uint QuestContextGroupId { get; set; }
    public bool AcceptWith { get; set; }
    public bool UseAlias { get; set; }
    public uint QuestActObjAliasId { get; set; }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) => currentObjectiveCount >= Math.Max(1, Count);

    public override void InitializeAction(Quest quest, QuestAct questAct)
    {
        base.InitializeAction(quest, questAct);
        if (AcceptWith)
        {
            var completed = QuestManager.Instance.GetGroupQuests(QuestContextGroupId)
                .Count(quest.Owner.Quests.HasQuestCompleted);
            SetObjective(quest, completed);
        }
        quest.Owner.Events.OnQuestComplete += questAct.OnQuestComplete;
    }

    public override void FinalizeAction(Quest quest, QuestAct questAct)
    {
        quest.Owner.Events.OnQuestComplete -= questAct.OnQuestComplete;
        base.FinalizeAction(quest, questAct);
    }

    public override void OnQuestComplete(QuestAct questAct, object sender, OnQuestCompleteArgs args)
    {
        if (questAct.Id == ActId && QuestManager.Instance.CheckGroupQuest(QuestContextGroupId, args.QuestId))
            AddObjective(questAct, 1);
    }
}
