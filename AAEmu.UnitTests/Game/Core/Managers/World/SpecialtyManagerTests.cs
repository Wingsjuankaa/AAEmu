using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Trading;

namespace AAEmu.UnitTests.Game.Core.Managers.World;

public class SpecialtyManagerTests
{
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
        FreshnessGroupItem[] stages =
        [
            new() { Id = 13, Time = 900, RewardRate = 1150, SellerShareRatio = 5 },
            new() { Id = 14, Time = 3_600, RewardRate = 1050, SellerShareRatio = 6 },
            new() { Id = 15, Time = 10_800, RewardRate = 900, SellerShareRatio = 7 },
            new() { Id = 16, Time = 86_400, RewardRate = 850, SellerShareRatio = 7 },
            new() { Id = 26, Time = 172_800, RewardRate = 650, SellerShareRatio = 10 }
        ];

        var result = SpecialtyManager.ResolveFreshnessStage(stages, elapsedSeconds);

        await Assert.That(result.Id).IsEqualTo(expectedStageId);
    }

    [Test]
    public async Task ResolveFreshnessStage_EmptyGroupReturnsNull()
    {
        var result = SpecialtyManager.ResolveFreshnessStage([], 1);

        await Assert.That(result).IsNull();
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
