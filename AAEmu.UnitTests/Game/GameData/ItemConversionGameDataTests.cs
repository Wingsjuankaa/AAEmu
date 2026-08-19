using AAEmu.Game.GameData;
using AAEmu.Game.Models.StaticValues;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.GameData;

public sealed class ItemConversionGameDataTests : IDisposable
{
    private readonly SqliteConnection _connection = new("Data Source=:memory:");

    public ItemConversionGameDataTests()
    {
        _connection.Open();
        Execute(@"
            CREATE TABLE item_convs (id INTEGER PRIMARY KEY, name TEXT, item_conv_set_id INTEGER);
            CREATE TABLE item_conv_rpack_members (id INTEGER PRIMARY KEY, item_conv_id INTEGER, item_conv_rpack_id INTEGER);
            CREATE TABLE item_conv_ppack_members (id INTEGER PRIMARY KEY, item_conv_id INTEGER, item_conv_ppack_id INTEGER);
            CREATE TABLE item_conv_reagents (id INTEGER PRIMARY KEY, item_conv_rpack_id INTEGER, item_id INTEGER, grade_id INTEGER, max_grade_id INTEGER);
            CREATE TABLE item_conv_reagent_filters (id INTEGER PRIMARY KEY, name TEXT, item_conv_rpack_id INTEGER, item_impl_id INTEGER, min_level INTEGER, max_level INTEGER, item_grade_id INTEGER, max_item_grade_id INTEGER, item_conv_epack_id INTEGER);
            CREATE TABLE item_conv_ppacks (id INTEGER PRIMARY KEY, name TEXT, chance_rate INTEGER);
            CREATE TABLE item_conv_products (id INTEGER PRIMARY KEY, item_conv_ppack_id INTEGER, item_id INTEGER, weight INTEGER, min INTEGER, max INTEGER, item_grade_id INTEGER);
        ");
    }

    [Test]
    public async Task Resolve_TraversesRpackRouteAndPpackInsteadOfMatchingPackIds()
    {
        Execute(@"
            INSERT INTO item_convs VALUES (4579, 'repackage_socket_red_3T', 8);
            INSERT INTO item_conv_rpack_members VALUES (1, 4579, 4579);
            INSERT INTO item_conv_ppack_members VALUES (1, 4579, 4652);
            INSERT INTO item_conv_reagents VALUES (1, 4579, 44684, 0, 12);
            INSERT INTO item_conv_ppacks VALUES (4579, 'unrelated_same_numeric_id', 10000);
            INSERT INTO item_conv_ppacks VALUES (4652, 'repackage_socket_red_3T', 10000);
            INSERT INTO item_conv_products VALUES (1, 4579, 44104, 1, 1, 1, -1);
            INSERT INTO item_conv_products VALUES (2, 4652, 44773, 1, 1, 1, -1);
        ");
        var data = new ItemConversionGameData();
        data.Load(_connection);

        var result = data.Resolve(8, 5, default, 44684, 1, _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.Route.Id).IsEqualTo((uint)4579);
        await Assert.That(result.Rewards.Count).IsEqualTo(1);
        await Assert.That(result.Rewards[0].ItemId).IsEqualTo((uint)44773);
        await Assert.That(result.Rewards[0].GradeId).IsEqualTo(-1);
    }

    [Test]
    public async Task Resolve_RejectsTheSameItemWhenTheEffectRequestsAnotherSet()
    {
        Execute(@"
            INSERT INTO item_convs VALUES (4579, 'repackage_socket_red_3T', 8);
            INSERT INTO item_conv_rpack_members VALUES (1, 4579, 4579);
            INSERT INTO item_conv_ppack_members VALUES (1, 4579, 4652);
            INSERT INTO item_conv_reagents VALUES (1, 4579, 44684, 0, 12);
            INSERT INTO item_conv_ppacks VALUES (4652, 'repackage_socket_red_3T', 10000);
            INSERT INTO item_conv_products VALUES (1, 4652, 44773, 1, 1, 1, -1);
        ");
        var data = new ItemConversionGameData();
        data.Load(_connection);

        var result = data.Resolve(7, 5, default, 44684, 1, _ => 0);

        await Assert.That(result.IsValid).IsFalse();
        await Assert.That(result.FailureReason).Contains("set 7");
    }

    [Test]
    public async Task Resolve_UsesWeightAndInclusiveAmountRange()
    {
        Execute(@"
            INSERT INTO item_convs VALUES (1, 'weighted', 8);
            INSERT INTO item_conv_rpack_members VALUES (1, 1, 10);
            INSERT INTO item_conv_ppack_members VALUES (1, 1, 20);
            INSERT INTO item_conv_reagents VALUES (1, 10, 100, 0, 12);
            INSERT INTO item_conv_ppacks VALUES (20, 'weighted', 10000);
            INSERT INTO item_conv_products VALUES (1, 20, 200, 3, 1, 1, 2);
            INSERT INTO item_conv_products VALUES (2, 20, 201, 2, 2, 4, 5);
        ");
        var rolls = new Queue<int>([4, 2]); // second weight bucket, then maximum amount offset
        var data = new ItemConversionGameData();
        data.Load(_connection);

        var result = data.Resolve(8, 5, default, 100, 1, _ => rolls.Dequeue());

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.Rewards[0].ItemId).IsEqualTo((uint)201);
        await Assert.That(result.Rewards[0].Amount).IsEqualTo(4);
        await Assert.That(result.Rewards[0].GradeId).IsEqualTo(5);
    }

    [Test]
    public async Task Resolve_RejectsAmbiguousRoutesInsteadOfChoosingByLoadOrder()
    {
        Execute(@"
            INSERT INTO item_convs VALUES (1, 'first', 8), (2, 'second', 8);
            INSERT INTO item_conv_rpack_members VALUES (1, 1, 10), (2, 2, 11);
            INSERT INTO item_conv_ppack_members VALUES (1, 1, 20), (2, 2, 21);
            INSERT INTO item_conv_reagents VALUES (1, 10, 100, 0, 12), (2, 11, 100, 0, 12);
            INSERT INTO item_conv_ppacks VALUES (20, 'first', 10000), (21, 'second', 10000);
            INSERT INTO item_conv_products VALUES (1, 20, 200, 1, 1, 1, -1), (2, 21, 201, 1, 1, 1, -1);
        ");
        var data = new ItemConversionGameData();
        data.Load(_connection);

        var result = data.Resolve(8, 5, default, 100, 1, _ => 0);

        await Assert.That(result.IsValid).IsFalse();
        await Assert.That(result.FailureReason).Contains("multiple routes");
    }

    [Test]
    public async Task CanonicalR575Catalog_WhenAvailable_ResolvesTheTransmuterProofRoute()
    {
        var repo = new DirectoryInfo(AppContext.BaseDirectory);
        while (repo is not null &&
               !(repo.Name == "AAEmu" && File.Exists(Path.Combine(repo.FullName, "AAEmu.slnx"))))
            repo = repo.Parent;

        if (repo?.Parent?.Parent is null)
            return;

        var databasePath = Path.Combine(
            repo.Parent.Parent.FullName,
            "data", "sqlite", "authoritative", "game_decrypted.sqlite3");
        if (!File.Exists(databasePath))
            return;

        await using var connection = new SqliteConnection($"Data Source={databasePath};Mode=ReadOnly");
        await connection.OpenAsync();
        var data = new ItemConversionGameData();
        data.Load(connection);

        var result = data.Resolve(8, 5, default, 44684, 1, _ => 0);

        await Assert.That(result.IsValid).IsTrue();
        await Assert.That(result.Route.Id).IsEqualTo((uint)4579);
        await Assert.That(result.Rewards).IsEquivalentTo([
            new AAEmu.Game.Models.Game.Items.ItemConversionReward(44773, 1, -1)
        ]);
    }

    private void Execute(string sql)
    {
        using var command = _connection.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    public void Dispose()
    {
        _connection.Dispose();
        GC.SuppressFinalize(this);
    }
}
