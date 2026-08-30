using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class DoodadBackpackWireTests
{
    [Test]
    public async Task TradePack_AdvertisesTemplateAndWritesCreationEpoch()
    {
        var createdAt = new DateTime(2026, 8, 27, 12, 50, 21, DateTimeKind.Utc);
        var template = new BackpackTemplate
        {
            Id = 17684,
            BackpackType = BackpackType.TradePack
        };

        var result = Doodad.ResolveItemWireData(template.Id, template, createdAt);

        await Assert.That(result.ItemTemplateId).IsEqualTo(17684u);
        await Assert.That(result.NeedsFreshness).IsTrue();
        await Assert.That(result.FreshnessTime)
            .IsEqualTo((ulong)new DateTimeOffset(createdAt).ToUnixTimeSeconds());
    }

    [Test]
    public async Task NonFreshBackpack_DoesNotAppendConditionalPayload()
    {
        var template = new BackpackTemplate
        {
            Id = 14677,
            BackpackType = BackpackType.Glider
        };

        var result = Doodad.ResolveItemWireData(template.Id, template, DateTime.UtcNow);

        await Assert.That(result.ItemTemplateId).IsEqualTo(14677u);
        await Assert.That(result.NeedsFreshness).IsFalse();
        await Assert.That(result.FreshnessTime).IsEqualTo(0UL);
    }

    [Test]
    public async Task OrdinaryRecoverableDecoration_AdvertisesItemWithoutFreshnessPayload()
    {
        var template = new ItemTemplate { Id = 98 };
        var result = Doodad.ResolveItemWireData(template.Id, template, DateTime.UtcNow);

        await Assert.That(result.ItemTemplateId).IsEqualTo(98u);
        await Assert.That(result.NeedsFreshness).IsFalse();
        await Assert.That(result.FreshnessTime).IsEqualTo(0UL);
    }

    [Test]
    public async Task NullItemSentinel_RemainsZeroWithoutConditionalPayload()
    {
        var result = Doodad.ResolveItemWireData(0, null, DateTime.UtcNow);

        await Assert.That(result.ItemTemplateId).IsEqualTo(0u);
        await Assert.That(result.NeedsFreshness).IsFalse();
        await Assert.That(result.FreshnessTime).IsEqualTo(0UL);
    }
}
