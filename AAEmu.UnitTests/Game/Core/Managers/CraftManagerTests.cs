using AAEmu.Game.Core.Managers;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Core.Managers;

public sealed class CraftManagerTests : IDisposable
{
    private readonly SqliteConnection _connection = new("Data Source=:memory:");

    public CraftManagerTests()
    {
        _connection.Open();
        using var command = _connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE crafts (
                id INTEGER PRIMARY KEY, cast_delay INTEGER, skill_id INTEGER, wi_id INTEGER,
                milestone_id INTEGER, req_doodad_id INTEGER, actability_limit INTEGER,
                recommend_level INTEGER, visible_order INTEGER, enable TEXT, products_pack_id INTEGER,
                use_only_actability TEXT, craft_c_category_id INTEGER, craft_d_category_id INTEGER,
                orderable TEXT, cost INTEGER);
            CREATE TABLE craft_products (
                id INTEGER PRIMARY KEY, craft_id INTEGER, item_id INTEGER, amount INTEGER,
                rate INTEGER, use_grade TEXT, item_grade_id INTEGER);
            CREATE TABLE craft_materials (
                id INTEGER PRIMARY KEY, craft_id INTEGER, item_id INTEGER, amount INTEGER,
                main_grade TEXT, require_grade INTEGER, upper_grade TEXT);
            CREATE TABLE craft_pack_crafts (
                id INTEGER PRIMARY KEY, craft_pack_id INTEGER, craft_id INTEGER);
            INSERT INTO crafts VALUES
                (1, 3000, 100, 7, 8, 9, 10, 11, 12, 't', 13, 't', 14, 15, 't', 16),
                (2, 1000, 101, 0, NULL, NULL, 0, 0, 0, 'f', NULL, 'f', NULL, NULL, 'f', 0),
                (3, 1000, 102, 0, NULL, NULL, 0, 0, 0, 't', NULL, 'f', NULL, NULL, 'f', 0);
            INSERT INTO craft_products VALUES
                (1, 1, 200, 3, 50, 't', 4),
                (2, 3, 201, 1, 100, 'f', 0);
            INSERT INTO craft_materials VALUES (1, 1, 300, 5, 't', 2, 't');
            INSERT INTO craft_pack_crafts VALUES (1, 77, 1);
            """;
        command.ExecuteNonQuery();
    }

    [Test]
    public async Task LoadsExactAa10FieldsAndPackMembership()
    {
        var manager = new CraftManager();
        manager.Load(_connection, new HashSet<uint> { 1 });

        var found = manager.TryGetCraft(1, out var craft);

        await Assert.That(found).IsTrue();
        await Assert.That(craft.CastDelay).IsEqualTo(3000);
        await Assert.That(craft.Cost).IsEqualTo(16);
        await Assert.That(craft.ProductsPackId).IsEqualTo(13u);
        await Assert.That(craft.UseOnlyActability).IsTrue();
        await Assert.That(craft.CraftCCategoryId).IsEqualTo(14u);
        await Assert.That(craft.CraftDCategoryId).IsEqualTo(15u);
        await Assert.That(craft.Orderable).IsTrue();
        await Assert.That(craft.CraftPackIds).Contains(77u);
        await Assert.That(craft.CraftMaterials[0].RequireGrade).IsEqualTo(2);
        await Assert.That(craft.CraftMaterials[0].UpperGrade).IsTrue();
        await Assert.That(craft.CraftProducts[0].Rate).IsEqualTo(50);
        await Assert.That(craft.CraftProducts[0].UseGrade).IsTrue();
        await Assert.That(craft.CraftProducts[0].ItemGradeId).IsEqualTo(4u);
    }

    [Test]
    public async Task DisabledAndUnknownRecipesNeverThrowOrResolveExecutable()
    {
        var manager = new CraftManager();
        manager.Load(_connection, new HashSet<uint> { 1 });

        await Assert.That(manager.TryGetCraft(2, out _)).IsFalse();
        await Assert.That(manager.TryGetCraft(3, out _)).IsFalse();
        await Assert.That(manager.TryGetCraft(999, out _)).IsFalse();
        await Assert.That(manager.HasCraft(2)).IsFalse();
        await Assert.That(manager.TryGetAnyCraft(2, out var disabled)).IsTrue();
        await Assert.That(disabled.Enable).IsFalse();
        await Assert.That(manager.TryGetAnyCraft(3, out var blocked)).IsTrue();
        await Assert.That(blocked.Enable).IsTrue();
    }

    [Test]
    public async Task RuntimePolicyLoadsExactPromotedSet()
    {
        var policy = CraftManager.LoadRuntimePolicy(
            Path.Combine(AppContext.BaseDirectory, "Data", "aa10-crafting-wave5-policy.json"));

        await Assert.That(policy.ExecutableCraftIds).Count().IsGreaterThan(7306);
        await Assert.That(policy.ExecutableCraftIds).DoesNotContain(0u);
        await Assert.That(policy.MaterialFreeCraftIds)
            .IsEquivalentTo(new uint[]
            {
                9267, 12149, 12150, 12151, 12152, 12177, 12178, 12189,
                12190, 12250, 12251, 12252, 12253, 12254
            });
    }

    [Test]
    public async Task MaterialFreeFlagIsAppliedOnlyByTheClosedPolicySet()
    {
        var manager = new CraftManager();
        manager.Load(
            _connection,
            new HashSet<uint> { 1, 3 },
            new HashSet<uint> { 3 });

        await Assert.That(manager.TryGetCraft(1, out var ordinary)).IsTrue();
        await Assert.That(ordinary.AllowEmptyMaterials).IsFalse();
        await Assert.That(manager.TryGetCraft(3, out var materialFree)).IsTrue();
        await Assert.That(materialFree.AllowEmptyMaterials).IsTrue();
    }

    public void Dispose() => _connection.Dispose();
}
