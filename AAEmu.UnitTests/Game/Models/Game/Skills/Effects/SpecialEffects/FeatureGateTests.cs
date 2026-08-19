using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Synthesis is gated at its entry point, before validation, RNG, payment or item mutation.
/// </summary>
public class FeatureGateTests
{
    private static FeatureSet With(Feature feature, bool enabled)
    {
        var features = new FeatureSet();
        features.Set(feature, enabled);
        return features;
    }

    [Test]
    public async Task Synthesis_IsRefusedWhenDisabled()
    {
        await Assert.That(ItemEvolving.IsFeatureEnabled(With(Feature.itemEvolving, false))).IsFalse();
    }

    [Test]
    public async Task Synthesis_IsAllowedWhenEnabled()
    {
        await Assert.That(ItemEvolving.IsFeatureEnabled(With(Feature.itemEvolving, true))).IsTrue();
    }

    [Test]
    public async Task NoFeatureSet_FailsClosed()
    {
        // Before the feature set is built, absence must read as "disabled" rather than as permission.
        await Assert.That(ItemEvolving.IsFeatureEnabled(null)).IsFalse();
    }

    [Test]
    public async Task DefaultFeatureSet_LeavesSynthesisDisabled()
    {
        var features = new FeatureSet();

        await Assert.That(ItemEvolving.IsFeatureEnabled(features)).IsFalse();
    }

    [Test]
    public async Task LunagemExtraction_IsRefusedWhenSocketExtractIsDisabled()
    {
        await Assert.That(ItemSocketing.IsExtractionFeatureEnabled(
            With(Feature.socketExtract, false))).IsFalse();
    }

    [Test]
    public async Task LunagemExtraction_IsAllowedWhenSocketExtractIsEnabled()
    {
        await Assert.That(ItemSocketing.IsExtractionFeatureEnabled(
            With(Feature.socketExtract, true))).IsTrue();
    }

    [Test]
    public async Task LunagemExtraction_FailsClosedWithoutFeatureSet()
    {
        await Assert.That(ItemSocketing.IsExtractionFeatureEnabled(null)).IsFalse();
    }

    [Test]
    public async Task ItemSmelting_RequiresItsFeatureBit()
    {
        await Assert.That(ItemSmeltingService.IsFeatureEnabled(
            With(Feature.itemSmelting, false))).IsFalse();
        await Assert.That(ItemSmeltingService.IsFeatureEnabled(
            With(Feature.itemSmelting, true))).IsTrue();
        await Assert.That(ItemSmeltingService.IsFeatureEnabled(null)).IsFalse();
    }
}
