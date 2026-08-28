using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingPlacementPolicyTests
{
    [Test]
    [Arguments(HousingPermission.Private, 7u, 70u, true)]
    [Arguments(HousingPermission.Private, 8u, 70u, true)]
    [Arguments(HousingPermission.Private, 8u, 80u, false)]
    [Arguments(HousingPermission.Family, 8u, 80u, true, true, false)]
    [Arguments(HousingPermission.Guild, 8u, 80u, true, false, true)]
    [Arguments(HousingPermission.Public, 8u, 80u, true)]
    public async Task HousingPermissionsPreserveSameAccountAndRejectUnrelatedPrivateCharacters(
        HousingPermission permission,
        uint characterId,
        uint characterAccountId,
        bool expected,
        bool sameFamily = false,
        bool sameGuild = false)
    {
        var allowed = HousingAccessPolicy.Allows(
            permission,
            alwaysPublic: false,
            unfinished: false,
            ownerId: 7,
            ownerAccountId: 70,
            characterId,
            characterAccountId,
            sameFamily,
            sameGuild);

        await Assert.That(allowed).IsEqualTo(expected);
    }

    [Test]
    public async Task AlwaysPublicAndUnfinishedHousingRemainAccessible()
    {
        await Assert.That(HousingAccessPolicy.Allows(
            HousingPermission.Private, true, false, 7, 70, 8, 80, false, false)).IsTrue();
        await Assert.That(HousingAccessPolicy.Allows(
            HousingPermission.Private, false, true, 7, 70, 8, 80, false, false)).IsTrue();
    }

    [Test]
    public async Task AuthorizedDesignRequiresExactDesignItemAndOwner()
    {
        var mappings = new[]
        {
            new HousingItemHousings { Design_Id = 41, Item_Id = 501 },
            new HousingItemHousings { Design_Id = 42, Item_Id = 502 }
        };

        var accepted = HousingPlacementPolicy.FindAuthorizedDesignItem(41, 501, 7, 7, mappings);
        var wrongItem = HousingPlacementPolicy.FindAuthorizedDesignItem(41, 502, 7, 7, mappings);
        var foreignOwner = HousingPlacementPolicy.FindAuthorizedDesignItem(41, 501, 8, 7, mappings);

        await Assert.That(accepted).IsSameReferenceAs(mappings[0]);
        await Assert.That(wrongItem).IsNull();
        await Assert.That(foreignOwner).IsNull();
    }

    [Test]
    public async Task AreaPolicyRequiresTheCompleteFootprintAndAllowedCategory()
    {
        var shape = Square(3, -10, -10, 10, 10);
        var catalog = HousingAreaShapeCatalog.Create([shape]);
        var areas = new Dictionary<uint, uint> { [3] = 90 };
        var categories = new Dictionary<uint, HashSet<uint>> { [90] = [12] };

        await Assert.That(HousingPlacementPolicy.IsCategoryAllowedForFootprint(
            "main_world", 0, 0, 9, 12, catalog, areas, categories)).IsTrue();
        await Assert.That(HousingPlacementPolicy.IsCategoryAllowedForFootprint(
            "main_world", 5, 0, 6, 12, catalog, areas, categories)).IsFalse();
        await Assert.That(HousingPlacementPolicy.IsCategoryAllowedForFootprint(
            "main_world", 0, 0, 9, 13, catalog, areas, categories)).IsFalse();
    }

    [Test]
    public async Task AreaCatalogRejectsMalformedAndUnknownWorldShapes()
    {
        var malformed = Square(0, -10, -10, 10, 10);
        var catalog = HousingAreaShapeCatalog.Create([malformed, Square(7, -5, -5, 5, 5)]);

        await Assert.That(catalog.ShapeCount).IsEqualTo(1);
        await Assert.That(catalog.FindContainingAreaIds("main_world", 0, 0, 1)).IsEquivalentTo([7u]);
        await Assert.That(catalog.FindContainingAreaIds("unknown", 0, 0, 1)).IsEmpty();
    }

    [Test]
    public async Task PlacementTransformRejectsNonFiniteWireValues()
    {
        await Assert.That(HousingPlacementPolicy.HasFiniteTransform(1, 2, 3, 4)).IsTrue();
        await Assert.That(HousingPlacementPolicy.HasFiniteTransform(
            1, 2, float.NaN, 4)).IsFalse();
        await Assert.That(HousingPlacementPolicy.HasFiniteTransform(
            1, 2, 3, 0, 0, 0, float.PositiveInfinity)).IsFalse();
    }

    [Test]
    public async Task TerrainEnvelopeSamplesTheWholeFootprint()
    {
        var accepted = HousingPlacementPolicy.EvaluateFootprintHeightEnvelope(
            10, 0, 0, 5, 2, 2, (_, _) => 10);
        var tooHigh = HousingPlacementPolicy.EvaluateFootprintHeightEnvelope(
            13, 0, 0, 5, 2, 2, (_, _) => 10);
        var tooLow = HousingPlacementPolicy.EvaluateFootprintHeightEnvelope(
            7, 0, 0, 5, 2, 2, (_, _) => 10);
        var invalid = HousingPlacementPolicy.EvaluateFootprintHeightEnvelope(
            10, 0, 0, 5, 2, 2, (_, _) => float.NaN);

        await Assert.That(accepted).IsEqualTo(HousingTerrainEnvelopeResult.Accepted);
        await Assert.That(tooHigh).IsEqualTo(HousingTerrainEnvelopeResult.TooHigh);
        await Assert.That(tooLow).IsEqualTo(HousingTerrainEnvelopeResult.TooLow);
        await Assert.That(invalid).IsEqualTo(HousingTerrainEnvelopeResult.Invalid);
    }

    [Test]
    public async Task CircularOverlapTreatsTouchingFootprintsAsAllowed()
    {
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            0, 0, 5, 9.99f, 0, 5)).IsTrue();
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            0, 0, 5, 10, 0, 5)).IsFalse();
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            0, 0, 0, 10, 0, 5)).IsFalse();
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            0, 0, -1, 10, 0, 5)).IsTrue();
    }

    [Test]
    public async Task NativeZeroRadiusSystemHousingDoesNotBlockPlayerPlacement()
    {
        // The twelve persisted Archeum Lodestones use housing_size 1, whose
        // AA10 garden_radius is exactly zero. They have no circular footprint.
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            13976, 14208, 11, 19643, 24385.4f, 0)).IsFalse();

        // A real nearby property with a demonstrated positive footprint still
        // blocks the exact same requested design.
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            13958, 14196, 11, 13940, 14196, 8)).IsTrue();
    }

    [Test]
    public async Task CircularOverlapAcceptsObservedFreeAA10Placement()
    {
        // Retail r575 sent CSCreateHouse for this placement after its native
        // OverlappedGrid/OverlappedObb gate accepted it. The nearest property
        // is the 8 m garden at (13940, 14196); the requested house is 14 m.
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            13962, 14198, 14, 13940, 14196, 8)).IsFalse();

        // Moving the same house inside the demonstrated combined radius must
        // still be rejected by the authoritative house-to-house server gate.
        await Assert.That(HousingPlacementPolicy.CircularFootprintsOverlap(
            13961, 14196, 14, 13940, 14196, 8)).IsTrue();
    }

    [Test]
    public async Task HousingPaymentRejectsShortCertificatesWithoutMutation()
    {
        var design = Item(1, 100, 2);
        var boundCertificates = Item(2, AAEmu.Game.Models.Game.Items.Item.BoundTaxCertificate, 3);
        var bag = Bag(design, boundCertificates);

        var committed = bag.TryConsumeHousingPlacementItems(
            design, 4, 0, [], [], [], []);

        await Assert.That(committed).IsFalse();
        await Assert.That(design.Count).IsEqualTo(2);
        await Assert.That(boundCertificates.Count).IsEqualTo(3);
        await Assert.That(bag.Items).Count().IsEqualTo(2);
    }

    [Test]
    public async Task HousingPaymentConsumesExactDesignAndAggregatedCertificatesAtomically()
    {
        var design = Item(1, 100, 2);
        var otherDesign = Item(2, 100, 2);
        var boundCertificates = Item(3, AAEmu.Game.Models.Game.Items.Item.BoundTaxCertificate, 3);
        var certificates = Item(4, AAEmu.Game.Models.Game.Items.Item.TaxCertificate, 4);
        var bag = Bag(design, otherDesign, boundCertificates, certificates);
        var designTasks = new List<ItemTask>();
        var taxTasks = new List<ItemTask>();

        var committed = bag.TryConsumeHousingPlacementItems(
            design, 2, 3, designTasks, [], taxTasks, []);

        await Assert.That(committed).IsTrue();
        await Assert.That(design.Count).IsEqualTo(1);
        await Assert.That(otherDesign.Count).IsEqualTo(2);
        await Assert.That(boundCertificates.Count).IsEqualTo(1);
        await Assert.That(certificates.Count).IsEqualTo(1);
        await Assert.That(designTasks).Count().IsEqualTo(1);
        await Assert.That(taxTasks).Count().IsEqualTo(2);
    }

    private static HousingAreaShapeTemplate Square(
        uint areaId, double minX, double minY, double maxX, double maxY) => new()
    {
        AreaId = areaId,
        World = "main_world",
        MinX = minX,
        MinY = minY,
        MaxX = maxX,
        MaxY = maxY,
        Points =
        [
            new HousingAreaShapePoint { X = minX, Y = minY },
            new HousingAreaShapePoint { X = maxX, Y = minY },
            new HousingAreaShapePoint { X = maxX, Y = maxY },
            new HousingAreaShapePoint { X = minX, Y = maxY }
        ]
    };

    private static ItemMock Item(uint id, uint templateId, int count) =>
        new(id, new ItemTemplate { Id = templateId, MaxCount = 1000 }, count);

    private static ItemContainer Bag(params Item[] items)
    {
        var bag = new ItemContainer(0, SlotType.Inventory, false, null)
        {
            ContainerSize = items.Length
        };
        for (var index = 0; index < items.Length; index++)
        {
            var item = items[index];
            item.SlotType = SlotType.Inventory;
            item.Slot = (byte)index;
            item._holdingContainer = bag;
            bag.Items.Add(item);
        }
        bag.UpdateFreeSlotCount();
        return bag;
    }
}
