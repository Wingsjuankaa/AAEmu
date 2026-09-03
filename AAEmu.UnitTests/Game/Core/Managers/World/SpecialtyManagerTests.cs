using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Trading;

namespace AAEmu.UnitTests.Game.Core.Managers.World;

public class SpecialtyManagerTests
{
    private static readonly FreshnessGroupItem[] DewstoneFineFreshnessStages =
    [
        new() { Id = 13, FreshnessGroupId = 5, Time = 900, RewardRate = 1150, SellerShareRatio = 5 },
        new() { Id = 14, FreshnessGroupId = 5, Time = 3_600, RewardRate = 1050, SellerShareRatio = 6 },
        new() { Id = 15, FreshnessGroupId = 5, Time = 10_800, RewardRate = 900, SellerShareRatio = 7 },
        new() { Id = 16, FreshnessGroupId = 5, Time = 86_400, RewardRate = 850, SellerShareRatio = 7 },
        new() { Id = 26, FreshnessGroupId = 5, Time = 172_800, RewardRate = 650, SellerShareRatio = 10 }
    ];

    [Test]
    public async Task Constructor_DoesNotCallDependencies()
    {
        var itemManager = Mock.Of<IItemManager>();

        var manager = new SpecialtyManager(itemManager.Object);

        await Assert.That(manager).IsNotNull();
        Mock.VerifyNoOtherCalls(itemManager);
    }

    [Test]
    [Arguments(0L, 13u)]
    [Arguments(900L, 13u)]
    [Arguments(901L, 14u)]
    [Arguments(3_600L, 14u)]
    [Arguments(3_601L, 15u)]
    [Arguments(172_800L, 26u)]
    [Arguments(172_801L, 26u)]
    public async Task ResolveFreshnessStage_UsesNativeInclusiveBoundaryAndFinalFallback(
        long elapsedSeconds,
        uint expectedStageId)
    {
        var result = SpecialtyManager.ResolveFreshnessStage(DewstoneFineFreshnessStages, elapsedSeconds);

        await Assert.That(result.Id).IsEqualTo(expectedStageId);
    }

    [Test]
    public async Task ResolveFreshnessStage_EmptyGroupReturnsNull()
    {
        var result = SpecialtyManager.ResolveFreshnessStage([], 1);

        await Assert.That(result).IsNull();
    }

    [Test]
    [Arguments(0L, 1150, 145_607)]
    [Arguments(900L, 1150, 145_607)]
    [Arguments(901L, 1050, 132_945)]
    [Arguments(3_600L, 1050, 132_945)]
    [Arguments(3_601L, 900, 113_953)]
    [Arguments(10_800L, 900, 113_953)]
    [Arguments(10_801L, 850, 107_622)]
    [Arguments(86_400L, 850, 107_622)]
    [Arguments(86_401L, 650, 82_300)]
    [Arguments(172_801L, 650, 82_300)]
    public async Task DewstoneToSolzreed_R575GoldenPayoutMatrix(
        long elapsedSeconds,
        int expectedFreshnessRate,
        int expectedPayout)
    {
        const int itemRefund = 10_000;
        const uint profit = 33_263;
        const int bundleRatio = 2_488;
        const int marketRatio = 130;
        const int mailInterestRate = 5;

        var stage = SpecialtyManager.ResolveFreshnessStage(DewstoneFineFreshnessStages, elapsedSeconds);
        var basePrice = SpecialtyManager.CalculateSpecialtyBasePrice(itemRefund, profit, bundleRatio);
        var calculation = SpecialtyManager.CalculateGoldPrice(
            basePrice,
            stage.RewardRate,
            marketRatio,
            mailInterestRate,
            specialtyGold: 1d,
            merchantPriceRatio: 1d,
            extraBuff: 1d);

        await Assert.That(basePrice).IsEqualTo(92_758);
        await Assert.That(stage.RewardRate).IsEqualTo(expectedFreshnessRate);
        await Assert.That(calculation.TotalPayout).IsEqualTo(expectedPayout);
    }

    [Test]
    public async Task FreshCraftDeliveredTenMinutesLater_UsesHighestFreshnessAndPaysFourteenGold()
    {
        var createdAtUtc = new DateTime(2026, 8, 30, 12, 0, 0, DateTimeKind.Utc);
        var soldAtUtc = createdAtUtc.AddMinutes(10);

        var stage = SpecialtyManager.ResolveFreshnessStageAt(
            DewstoneFineFreshnessStages,
            createdAtUtc,
            soldAtUtc);
        var ageSeconds = SpecialtyManager.CalculateFreshnessAgeSeconds(createdAtUtc, soldAtUtc);
        var basePrice = SpecialtyManager.CalculateSpecialtyBasePrice(10_000, 33_263, 2_488);
        var calculation = SpecialtyManager.CalculateGoldPrice(
            basePrice,
            stage.RewardRate,
            specialtyRatio: 130,
            interestRate: 5,
            specialtyGold: 1d,
            merchantPriceRatio: 1d,
            extraBuff: 1d);

        await Assert.That(ageSeconds).IsEqualTo(600L);
        await Assert.That(stage.RewardRate).IsEqualTo(1150);
        await Assert.That(calculation.TotalPayout).IsEqualTo(145_607);
    }

    [Test]
    public async Task MysqlUnspecifiedCraftTimestamp_IsInterpretedAsUtcWithoutAgingThePack()
    {
        var createdAtFromMysql = new DateTime(2026, 8, 30, 12, 0, 0, DateTimeKind.Unspecified);
        var soldAtUtc = new DateTime(2026, 8, 30, 12, 10, 0, DateTimeKind.Utc);

        var stage = SpecialtyManager.ResolveFreshnessStageAt(
            DewstoneFineFreshnessStages,
            createdAtFromMysql,
            soldAtUtc);

        await Assert.That(stage.RewardRate).IsEqualTo(1150);
    }

    [Test]
    [Arguments(130, 145_607)]
    [Arguments(100, 112_005)]
    [Arguments(70, 78_404)]
    public async Task FreshDewstonePack_AppliesMarketDemandExactlyOnce(int marketRatio, int expectedPayout)
    {
        var basePrice = SpecialtyManager.CalculateSpecialtyBasePrice(10_000, 33_263, 2_488);

        var calculation = SpecialtyManager.CalculateGoldPrice(
            basePrice,
            freshnessRate: 1150,
            specialtyRatio: marketRatio,
            interestRate: 5,
            specialtyGold: 1d,
            merchantPriceRatio: 1d,
            extraBuff: 1d);

        await Assert.That(calculation.TotalPayout).IsEqualTo(expectedPayout);
    }

    [Test]
    public async Task NativeFormulaFactors_AreAppliedBeforeMailInterest()
    {
        var basePrice = SpecialtyManager.CalculateSpecialtyBasePrice(10_000, 33_263, 2_488);

        var calculation = SpecialtyManager.CalculateGoldPrice(
            basePrice,
            freshnessRate: 1150,
            specialtyRatio: 130,
            interestRate: 5,
            specialtyGold: 1d,
            merchantPriceRatio: 1.10d,
            extraBuff: 1d);

        await Assert.That(calculation.TotalPayout).IsEqualTo(160_168);
    }

    [Test]
    public async Task TryGetAcceptedBundleItem_SelectsEquippedPackForDestinationBundle()
    {
        var template = new BackpackTemplate { Id = 31_856, FreshnessGroupId = 5 };
        var backpack = new Backpack { TemplateId = template.Id, Template = template };
        var expected = new SpecialtyBundleItem
        {
            ItemId = template.Id,
            SpecialtyBundleId = 10,
            Item = template
        };
        Dictionary<uint, Dictionary<uint, SpecialtyBundleItem>> mappings = new()
        {
            [template.Id] = new() { [10] = expected }
        };

        var found = SpecialtyManager.TryGetAcceptedBundleItem(backpack, 10, mappings, out var actual);

        await Assert.That(found).IsTrue();
        await Assert.That(actual).IsSameReferenceAs(expected);
    }

    [Test]
    public async Task TryGetAcceptedBundleItem_RejectsPackOutsideDestinationBundle()
    {
        var template = new BackpackTemplate { Id = 31_856 };
        var backpack = new Backpack { TemplateId = template.Id, Template = template };
        Dictionary<uint, Dictionary<uint, SpecialtyBundleItem>> mappings = new()
        {
            [template.Id] = new()
            {
                [26] = new SpecialtyBundleItem
                {
                    ItemId = template.Id,
                    SpecialtyBundleId = 26,
                    Item = template
                }
            }
        };

        var found = SpecialtyManager.TryGetAcceptedBundleItem(backpack, 10, mappings, out var actual);

        await Assert.That(found).IsFalse();
        await Assert.That(actual).IsNull();
    }

    [Test]
    [Arguments(0u, 1_797u, true)]
    [Arguments(1_797u, 1_797u, true)]
    [Arguments(711u, 1_797u, false)]
    public async Task IsSelfTarget_AcceptsNativeZeroSentinelOrActiveCharacterOnly(
        uint packetCharacterObjId,
        uint activeCharacterObjId,
        bool expected)
    {
        var actual = SpecialtyManager.IsSelfTarget(packetCharacterObjId, activeCharacterObjId);

        await Assert.That(actual).IsEqualTo(expected);
    }
}
