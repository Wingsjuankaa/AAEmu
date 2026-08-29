using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.Housing;

using Newtonsoft.Json;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingInteractionCatalogTests
{
    [Test]
    public async Task TryGetBindings_ReturnsStableNativeIdentityOrder()
    {
        var catalog = HousingInteractionCatalog.Create([
            Definition(313, AttachPointKind.HealPoint2, 4565),
            Definition(313, AttachPointKind.Driver, 4925),
            Definition(313, AttachPointKind.HealPoint0, 4561),
            Definition(99, AttachPointKind.NamePlate01, 2392)
        ]);

        var found = catalog.TryGetBindings(313, out var bindings);

        await Assert.That(found).IsTrue();
        await Assert.That(bindings.Select(x => (byte)x.AttachPointId))
            .IsEquivalentTo(new byte[]
            {
                (byte)AttachPointKind.Driver,
                (byte)AttachPointKind.HealPoint0,
                (byte)AttachPointKind.HealPoint2
            });
        await Assert.That(catalog.BindingCount).IsEqualTo(4);
        await Assert.That(catalog.HousingTemplateCount).IsEqualTo(2);
    }

    [Test]
    public async Task MissingLookup_FailsClosedWithoutThrowing()
    {
        var catalog = HousingInteractionCatalog.Create([
            Definition(313, AttachPointKind.Driver, 4925)
        ]);

        var foundHousing = catalog.TryGetBindings(999, out var bindings);
        var foundDefinition = catalog.TryGetDefinition(313, (byte)AttachPointKind.Driver, 999, out var definition);

        await Assert.That(foundHousing).IsFalse();
        await Assert.That(bindings).IsEmpty();
        await Assert.That(foundDefinition).IsFalse();
        await Assert.That(definition).IsNull();
    }

    [Test]
    public void DuplicateNativeIdentity_IsRejected()
    {
        var first = Definition(313, AttachPointKind.Driver, 4925);
        var duplicate = first with { ForceDbSave = true };

        Assert.Throws<InvalidDataException>(() => HousingInteractionCatalog.Create([first, duplicate]));
    }

    [Test]
    public async Task BlockedOrInvalidTransform_IsNeverExecutable()
    {
        var blocked = Definition(313, AttachPointKind.Driver, 4925) with
        {
            BlockReason = HousingInteractionBlockReason.MissingConsumer
        };
        var nonUniform = Definition(313, AttachPointKind.Driver, 4925) with
        {
            Transform = new HousingLocalTransform { ScaleX = 1, ScaleY = 2, ScaleZ = 1 }
        };
        var noSource = Definition(313, AttachPointKind.Driver, 4925) with
        {
            PositionSource = HousingBindingPositionSource.None
        };

        await Assert.That(blocked.IsExecutable).IsFalse();
        await Assert.That(nonUniform.IsExecutable).IsFalse();
        await Assert.That(noSource.IsExecutable).IsFalse();
    }

    [Test]
    public async Task ExplicitOriginTransform_IsNotTreatedAsMissingEvidence()
    {
        var definition = Definition(313, AttachPointKind.Driver, 4925);

        await Assert.That(definition.Transform.Position).IsEqualTo(System.Numerics.Vector3.Zero);
        await Assert.That(definition.IsExecutable).IsTrue();
    }

    [Test]
    public async Task GeneratedH3Catalog_PromotesExactlyStoneRoseFive()
    {
        var repositoryRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(repositoryRoot, "AAEmu.Game", "Data", "housing_interactions_aa10_h3.json");
        var file = JsonConvert.DeserializeObject<HousingInteractionCatalogFile>(File.ReadAllText(path));

        await Assert.That(file).IsNotNull();
        await Assert.That(file!.SchemaVersion).IsEqualTo(HousingInteractionCatalog.CurrentSchemaVersion);
        await Assert.That(file.ClientBuild).IsEqualTo("10.0.2.13-r575");
        await Assert.That(file.Bindings.Count).IsEqualTo(4646);
        await Assert.That(file.Bindings.Count(x => x.ForceDbSave)).IsEqualTo(102);

        var promoted = file.Bindings.Where(x => x.IsExecutable).ToArray();
        await Assert.That(promoted.Length).IsEqualTo(5);
        await Assert.That(promoted.All(x => x.HousingTemplateId == 313)).IsTrue();
        await Assert.That(promoted.Select(x => (byte)x.AttachPointId).Order().ToArray())
            .IsEquivalentTo(new byte[] { 1, 36, 37, 38, 57 });
        await Assert.That(promoted.All(x => x.Transform.Position != System.Numerics.Vector3.Zero)).IsTrue();

        var catalog = HousingInteractionCatalog.Create(file.Bindings);
        await Assert.That(catalog.BindingCount).IsEqualTo(4646);
    }

    [Test]
    public async Task GeneratedH4Catalog_PromotesResidentialStructureAndKeepsServicesClosed()
    {
        var repositoryRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(repositoryRoot, "AAEmu.Game", "Data", "housing_interactions_aa10_h4.json");
        var file = JsonConvert.DeserializeObject<HousingInteractionCatalogFile>(File.ReadAllText(path));

        await Assert.That(file).IsNotNull();
        await Assert.That(file!.SchemaVersion).IsEqualTo(HousingInteractionCatalog.CurrentSchemaVersion);
        await Assert.That(file.ClientBuild).IsEqualTo("10.0.2.13-r575");
        await Assert.That(file.Bindings.Count).IsEqualTo(4646);
        await Assert.That(file.Bindings.Count(x => x.ForceDbSave)).IsEqualTo(102);

        var stoneRose = file.Bindings.Where(x => x.HousingTemplateId == 313 && x.IsExecutable).ToArray();
        await Assert.That(stoneRose.Length).IsEqualTo(5);

        var tradesmans = file.Bindings.Where(x => x.HousingTemplateId == 437).ToArray();
        await Assert.That(tradesmans.Count(x => x.IsExecutable)).IsEqualTo(6);
        await Assert.That(tradesmans.Where(x => x.IsExecutable).Select(x => (byte)x.AttachPointId).Order().ToArray())
            .IsEquivalentTo(new byte[] { 1, 12, 36, 37, 38, 57 });
        await Assert.That(tradesmans.Where(x => !x.IsExecutable).Select(x => (byte)x.AttachPointId).Order().ToArray())
            .IsEquivalentTo(new byte[] { 9, 10, 11, 45 });
        await Assert.That(tradesmans.All(x => x.PositionSource == HousingBindingPositionSource.Aa10ModelHelper))
            .IsTrue();

        await Assert.That(file.Bindings.Any(x =>
            x.BlockReason == HousingInteractionBlockReason.TerritorialSubsystemRequired)).IsTrue();
        await Assert.That(file.Bindings.Any(x =>
            x.BlockReason == HousingInteractionBlockReason.MissingConsumer)).IsTrue();
    }

    [Test]
    public async Task GeneratedH5Catalog_PromotesCraftingServicesAndKeepsQuestClosed()
    {
        var repositoryRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(repositoryRoot, "AAEmu.Game", "Data", "housing_interactions_aa10_h5.json");
        var file = JsonConvert.DeserializeObject<HousingInteractionCatalogFile>(File.ReadAllText(path));

        await Assert.That(file).IsNotNull();
        await Assert.That(file!.SchemaVersion).IsEqualTo(HousingInteractionCatalog.CurrentSchemaVersion);
        await Assert.That(file.ClientBuild).IsEqualTo("10.0.2.13-r575");
        await Assert.That(file.Bindings.Count).IsEqualTo(4646);
        await Assert.That(file.Bindings.Count(x => x.IsExecutable)).IsEqualTo(3889);
        await Assert.That(file.Bindings.Count(x => x.ForceDbSave)).IsEqualTo(102);

        var tradesmans = file.Bindings.Where(x => x.HousingTemplateId == 437).ToArray();
        await Assert.That(tradesmans.Count(x => x.IsExecutable)).IsEqualTo(9);
        await Assert.That(tradesmans.Where(x => x.IsExecutable).Select(x => (byte)x.AttachPointId).Order().ToArray())
            .IsEquivalentTo(new byte[] { 1, 9, 11, 12, 36, 37, 38, 45, 57 });

        var questBinding = tradesmans.Single(x => (byte)x.AttachPointId == 10);
        await Assert.That(questBinding.DoodadId).IsEqualTo(9142u);
        await Assert.That(questBinding.BlockReason)
            .IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
    }

    [Test]
    public async Task GeneratedH5BCatalog_PromotesOnlyProvenResidentialProvidersAndPlots()
    {
        var repositoryRoot = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(repositoryRoot, "AAEmu.Game", "Data", "housing_interactions_aa10_h5b.json");
        var file = JsonConvert.DeserializeObject<HousingInteractionCatalogFile>(File.ReadAllText(path));

        await Assert.That(file).IsNotNull();
        await Assert.That(file!.SchemaVersion).IsEqualTo(HousingInteractionCatalog.CurrentSchemaVersion);
        await Assert.That(file.ClientBuild).IsEqualTo("10.0.2.13-r575");
        await Assert.That(file.Bindings.Count).IsEqualTo(4646);
        await Assert.That(file.Bindings.Count(x => x.IsExecutable)).IsEqualTo(3990);
        await Assert.That(file.Bindings.Count(x => x.ForceDbSave)).IsEqualTo(102);

        uint[] waterProviderDoodads = [5539, 9344, 13119, 13492, 14769, 17161, 17637, 18226];
        var waterBindings = file.Bindings
            .Where(x => waterProviderDoodads.Contains(x.DoodadId))
            .ToArray();
        await Assert.That(waterBindings.Length).IsEqualTo(25);
        await Assert.That(waterBindings.All(x => x.IsExecutable)).IsTrue();

        var thatched = file.Bindings.Where(x => x.HousingTemplateId == 330).ToArray();
        await Assert.That(thatched.Length).IsEqualTo(6);
        await Assert.That(thatched.All(x => x.IsExecutable)).IsTrue();

        var waterBarrel = thatched.Single(x => x.DoodadId == 5539);
        await Assert.That((byte)waterBarrel.AttachPointId).IsEqualTo((byte)AttachPointKind.Cannon0);
        await Assert.That(waterBarrel.PositionSource)
            .IsEqualTo(HousingBindingPositionSource.Aa10ModelHelper);

        var tradesmansQuest = file.Bindings.Single(x =>
            x.HousingTemplateId == 437 && x.DoodadId == 9142);
        await Assert.That(tradesmansQuest.BlockReason)
            .IsEqualTo(HousingInteractionBlockReason.PendingWavePromotion);
        await Assert.That(file.Bindings.Any(x =>
            x.BlockReason == HousingInteractionBlockReason.MissingConsumer)).IsTrue();

        var planterBindings = file.Bindings.Where(x => x.DoodadId == 9108).ToArray();
        await Assert.That(planterBindings.Length).IsEqualTo(73);
        await Assert.That(planterBindings.Select(x => x.HousingTemplateId).Distinct().Count())
            .IsEqualTo(37);
        await Assert.That(planterBindings.All(x => x.IsExecutable)).IsTrue();

        var upgradedThatchedPlanters = planterBindings
            .Where(x => x.HousingTemplateId == 434)
            .OrderBy(x => (byte)x.AttachPointId)
            .ToArray();
        await Assert.That(upgradedThatchedPlanters.Select(x => (byte)x.AttachPointId).ToArray())
            .IsEquivalentTo(new byte[]
            {
                (byte)AttachPointKind.HealPoint6,
                (byte)AttachPointKind.HealPoint7
            });

        var rancherPens = file.Bindings
            .Where(x => x.DoodadId == 9352)
            .OrderBy(x => x.HousingTemplateId)
            .ToArray();
        await Assert.That(rancherPens.Length).IsEqualTo(3);
        await Assert.That(rancherPens.Select(x => x.HousingTemplateId).ToArray())
            .IsEquivalentTo(new uint[] { 403, 418, 433 });
        await Assert.That(rancherPens.All(x =>
            x.IsExecutable && x.AttachPointId == AttachPointKind.HealPoint8)).IsTrue();
    }

    private static HousingBindingDefinition Definition(
        uint housingId,
        AttachPointKind attachPoint,
        uint doodadId) =>
        new()
        {
            HousingTemplateId = housingId,
            AttachPointId = attachPoint,
            DoodadId = doodadId,
            Transform = new HousingLocalTransform(),
            PositionSource = HousingBindingPositionSource.Aa10ModelHelper
        };
}
