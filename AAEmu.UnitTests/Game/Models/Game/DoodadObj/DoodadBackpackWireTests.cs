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

        var result = Doodad.ResolveBackpackWireData(template, createdAt);

        await Assert.That(result.BackpackItemId).IsEqualTo(17684u);
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

        var result = Doodad.ResolveBackpackWireData(template, DateTime.UtcNow);

        await Assert.That(result.BackpackItemId).IsEqualTo(14677u);
        await Assert.That(result.NeedsFreshness).IsFalse();
        await Assert.That(result.FreshnessTime).IsEqualTo(0UL);
    }

    [Test]
    public async Task OrdinaryItem_DoesNotAdvertiseBackpackPayload()
    {
        var result = Doodad.ResolveBackpackWireData(new ItemTemplate { Id = 8000 }, DateTime.UtcNow);

        await Assert.That(result.BackpackItemId).IsEqualTo(0u);
        await Assert.That(result.NeedsFreshness).IsFalse();
        await Assert.That(result.FreshnessTime).IsEqualTo(0UL);
    }
}
