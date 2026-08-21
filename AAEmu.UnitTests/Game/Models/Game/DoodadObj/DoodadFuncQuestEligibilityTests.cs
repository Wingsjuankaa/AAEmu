using AAEmu.Game.Models.Game.DoodadObj.Funcs;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class DoodadFuncQuestEligibilityTests
{
    [Test]
    public async Task Offer_RejectsCompletedNonRepeatableQuest()
    {
        var eligible = DoodadFuncQuest.IsEligible(
            DoodadFuncQuest.OfferQuestKind, isActive: false, isComplete: true, repeatable: false);

        await Assert.That(eligible).IsFalse();
    }

    [Test]
    public async Task Offer_AcceptsNextIncompleteQuest()
    {
        var eligible = DoodadFuncQuest.IsEligible(
            DoodadFuncQuest.OfferQuestKind, isActive: false, isComplete: false, repeatable: false);

        await Assert.That(eligible).IsTrue();
    }

    [Test]
    public async Task Offer_AcceptsCompletedRepeatableQuest()
    {
        var eligible = DoodadFuncQuest.IsEligible(
            DoodadFuncQuest.OfferQuestKind, isActive: false, isComplete: true, repeatable: true);

        await Assert.That(eligible).IsTrue();
    }

    [Test]
    [Arguments(true, true)]
    [Arguments(false, false)]
    public async Task Report_RequiresActiveQuest(bool isActive, bool expected)
    {
        var eligible = DoodadFuncQuest.IsEligible(
            DoodadFuncQuest.ReportQuestKind, isActive, isComplete: false, repeatable: false);

        await Assert.That(eligible).IsEqualTo(expected);
    }
}
