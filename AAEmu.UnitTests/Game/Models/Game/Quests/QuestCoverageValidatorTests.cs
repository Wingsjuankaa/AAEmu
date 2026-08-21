using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestCoverageValidatorTests
{
    private static (QuestActTemplate BaseAct, QuestActTemplate Detail) CreatePair(bool enabled = true)
    {
        var quest = new QuestTemplate { Id = 7 };
        var component = new QuestComponentTemplate(quest) { Id = 11 };
        var baseAct = new QuestActTemplate(component)
        {
            ActId = 13,
            DetailId = 17,
            DetailType = nameof(QuestActSupplyCopper),
            Enabled = enabled
        };
        var detail = new QuestActSupplyCopper(component)
        {
            ActId = 13,
            DetailId = 17
        };
        return (baseAct, detail);
    }

    [Test]
    public async Task ExactEnabledActAndDetail_PassStrictGate()
    {
        var pair = CreatePair();
        var loaded = new Dictionary<string, Dictionary<uint, QuestActTemplate>>
        {
            [nameof(QuestActSupplyCopper)] = new() { [17] = pair.Detail }
        };

        var findings = QuestCoverageValidator.Validate([pair.BaseAct], loaded);

        await Assert.That(findings).IsEmpty();
        QuestCoverageValidator.Enforce(findings, QuestCoverageValidationMode.Strict);
    }

    [Test]
    public async Task MissingClass_IsVisibleAndStrictModeFails()
    {
        var pair = CreatePair();
        pair.BaseAct.DetailType = "QuestActMissingNativeContract";
        var findings = QuestCoverageValidator.Validate(
            [pair.BaseAct], new Dictionary<string, Dictionary<uint, QuestActTemplate>>());

        await Assert.That(findings.Select(x => x.Code)).Contains("missing_server_class");
        await Assert.That(() => QuestCoverageValidator.Enforce(findings, QuestCoverageValidationMode.Strict))
            .Throws<InvalidDataException>();
    }

    [Test]
    public async Task MissingLoaderDetail_IsVisibleButReportModeContinues()
    {
        var pair = CreatePair();
        var loaded = new Dictionary<string, Dictionary<uint, QuestActTemplate>>
        {
            [nameof(QuestActSupplyCopper)] = []
        };
        var findings = QuestCoverageValidator.Validate([pair.BaseAct], loaded);

        await Assert.That(findings.Select(x => x.Code)).Contains("missing_detail_or_loader");
        QuestCoverageValidator.Enforce(findings, QuestCoverageValidationMode.Report);
    }

    [Test]
    public async Task DisabledBaseAct_IsIntentionallyIgnored()
    {
        var pair = CreatePair(false);
        var loaded = new Dictionary<string, Dictionary<uint, QuestActTemplate>>
        {
            [nameof(QuestActSupplyCopper)] = []
        };

        var findings = QuestCoverageValidator.Validate([pair.BaseAct], loaded);

        await Assert.That(findings).IsEmpty();
    }

    [Test]
    public async Task MismatchedAndOrphanDetails_AreRejected()
    {
        var pair = CreatePair();
        pair.Detail.ActId = 99;
        var loaded = new Dictionary<string, Dictionary<uint, QuestActTemplate>>
        {
            [nameof(QuestActSupplyCopper)] = new() { [17] = pair.Detail }
        };

        var findings = QuestCoverageValidator.Validate([pair.BaseAct], loaded);

        await Assert.That(findings.Select(x => x.Code)).Contains("detail_attachment_mismatch");
        await Assert.That(findings.Select(x => x.Code)).Contains("orphan_detail_attachment");
    }
}
