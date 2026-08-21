using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public interface IQuestRewardPreflight
{
    bool CanApplyReward(Quest quest, QuestAct questAct);
}

public abstract class QuestActSupplyPhase4(QuestComponentTemplate parentComponent)
    : QuestActTemplate(parentComponent), IQuestRewardPreflight
{
    protected virtual QuestRewardCompletionMode CompletionMode => QuestRewardCompletionMode.AfterPersistence;
    protected abstract bool CanApplyCore(Quest quest, QuestAct questAct);
    protected abstract bool ApplyReward(Quest quest, QuestAct questAct);

    public bool CanApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardLedgerManager.Instance.CanExecute(quest, questAct, () => CanApplyCore(quest, questAct));

    public sealed override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount) =>
        QuestRewardLedgerManager.Instance.TryExecute(quest, questAct, () => ApplyReward(quest, questAct), CompletionMode);
}

public sealed class QuestActSupplyActability(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public uint ActabilityGroupId { get; set; }
    public int Point { get; set; }

    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character && Point >= 0 &&
        character.Actability.Actabilities.ContainsKey(ActabilityGroupId);

    protected override bool ApplyReward(Quest quest, QuestAct questAct)
    {
        var character = (Character)quest.Owner;
        if (Point == 0)
            return true;
        character.Actability.AddPoint(ActabilityGroupId, Point);
        character.Actability.Send();
        return true;
    }
}

public sealed class QuestActSupplyArchePassPoint(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Point { get; set; }

    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character && Point >= 0 &&
        ArchePassManager.Instance.CanAddQuestPoints(character, Point);
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        ArchePassManager.Instance.TryAddQuestPoints((Character)quest.Owner, Point);
}

public sealed class QuestActSupplyContributionPoint(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Point { get; set; }

    protected override bool CanApplyCore(Quest quest, QuestAct questAct)
    {
        if (quest.Owner is not Character character || Point < 0)
            return false;
        var member = character.Expedition?.GetMember(character);
        return member != null && (ulong)member.ContributionPoint + (uint)Point <= uint.MaxValue &&
               (ulong)member.WeeklyContributionPoint + (uint)Point <= uint.MaxValue;
    }

    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        ExpeditionManager.Instance.TryChangeContributionPoints((Character)quest.Owner, Point, true);
}

public sealed class QuestActSupplyExpeditionExp(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Point { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character { Expedition: not null } && Point >= 0;
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryAddExpeditionExp((Character)quest.Owner, Point);
}

public sealed class QuestActSupplyFactionChange(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public uint SystemFactionId { get; set; }
    public bool IgnoreLimit { get; set; }
    public bool InferiorEscape { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character &&
        QuestRewardProgressManager.Instance.CanChangeFaction(character, SystemFactionId);
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryChangeFaction((Character)quest.Owner, SystemFactionId, IgnoreLimit, InferiorEscape);
}

public sealed class QuestActSupplyFamilyExp(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Point { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character && QuestRewardProgressManager.Instance.CanAddFamilyExp(character, Point);
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryAddFamilyExp((Character)quest.Owner, Point);
}

public sealed class QuestActSupplyLeadershipPoint(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Point { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) => quest.Owner is Character && Point >= 0;
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryAddLeadership((Character)quest.Owner, Point);
}

public sealed class QuestActSupplyLocalLp(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int LocalLp { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) => quest.Owner is Character && LocalLp >= 0;
    protected override bool ApplyReward(Quest quest, QuestAct questAct)
    {
        ((Character)quest.Owner).AddLocalLaborPower(LocalLp);
        return true;
    }
}

public class QuestActSupplyRankedItem(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public int Rank { get; set; }
    public uint ItemId { get; set; }
    public byte GradeId { get; set; }
    protected virtual bool MatchesResult(Quest quest, int actualRank) => true;

    public static bool ShouldGrant(int configuredRank, int actualRank) =>
        configuredRank > 0 && actualRank == configuredRank;

    protected override bool CanApplyCore(Quest quest, QuestAct questAct) => quest.GetCompetitionRank(false) > 0;
    protected override bool ApplyReward(Quest quest, QuestAct questAct)
    {
        var actualRank = quest.GetCompetitionRank(false);
        if (ShouldGrant(Rank, actualRank) && MatchesResult(quest, actualRank))
            quest.QuestRewardItemsPool.Add(new ItemCreationDefinition(ItemId, Count, GradeId));
        return true;
    }
}

public sealed class QuestActSupplyResidentCharge(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public uint ZoneGroupId { get; set; }
    public int Charge { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character &&
        QuestRewardProgressManager.Instance.CanAddResidentCharge(character, ZoneGroupId, Charge);
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryAddResidentCharge((Character)quest.Owner, ZoneGroupId, Charge);
}

public sealed class QuestActSupplyResidentPoint(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public uint ZoneGroupId { get; set; }
    public int Point { get; set; }
    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest.Owner is Character character &&
        QuestRewardProgressManager.Instance.CanAddResidentPoint(character, ZoneGroupId, Point);
    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        QuestRewardProgressManager.Instance.TryAddResidentPoint((Character)quest.Owner, ZoneGroupId, Point);
}

public sealed class QuestActSupplyResultRankedItem(QuestComponentTemplate parentComponent) : QuestActSupplyRankedItem(parentComponent)
{
    public bool Result { get; set; }
    protected override bool MatchesResult(Quest quest, int actualRank) =>
        quest.GetCompetitionRank(true) == actualRank && Result == (actualRank == 1);
}
