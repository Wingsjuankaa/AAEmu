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
