using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Items.Templates;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.GameData;

public sealed class ItemSecurityGameDataTests : IDisposable
{
    private readonly SqliteConnection _connection = new("Data Source=:memory:");

    public ItemSecurityGameDataTests()
    {
        _connection.Open();
        using var command = _connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE item_categories (id INTEGER PRIMARY KEY, secure TEXT NOT NULL);
            CREATE TABLE item_secure_exceptions (id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL);
            CREATE TABLE content_configs (id INTEGER PRIMARY KEY, kind_id INTEGER NOT NULL, value INTEGER NOT NULL);
            INSERT INTO item_categories VALUES (10, 't'), (11, 'f');
            INSERT INTO item_secure_exceptions VALUES (1, 1002);
            INSERT INTO content_configs VALUES
                (43, 14, 4320), (214, 14, 0), (215, 14, 1), (222, 14, 0), (223, 14, 0);
            """;
        command.ExecuteNonQuery();
    }

    [Test]
    public async Task Load_UsesExactR575EligibilityAndConfiguration()
    {
        var data = new ItemSecurityGameData();
        data.Load(_connection);

        await Assert.That(data.SecureCategoryCount).IsEqualTo(1);
        await Assert.That(data.ExceptionItemCount).IsEqualTo(1);
        await Assert.That(data.UnlockDelay).IsEqualTo(TimeSpan.FromHours(72));
        await Assert.That(data.MoneyCost).IsEqualTo(0L);
        await Assert.That(data.UseEquipmentUi).IsTrue();
        await Assert.That(data.UseSecondPasswordWhenLocking).IsFalse();
        await Assert.That(data.UseSecondPasswordWhenUnlocking).IsFalse();
        await Assert.That(data.IsEligible(new ItemTemplate { Id = 1001, CategoryId = 10 })).IsTrue();
        await Assert.That(data.IsEligible(new ItemTemplate { Id = 1002, CategoryId = 10 })).IsFalse();
        await Assert.That(data.IsEligible(new ItemTemplate { Id = 1003, CategoryId = 11 })).IsFalse();
    }

    [Test]
    public async Task CanonicalR575Catalog_WhenAvailable_HasClosedItemLockCounts()
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
        var data = new ItemSecurityGameData();
        data.Load(connection);

        await Assert.That(data.SecureCategoryCount).IsEqualTo(30);
        await Assert.That(data.ExceptionItemCount).IsEqualTo(803);
        await Assert.That(data.UnlockDelay).IsEqualTo(TimeSpan.FromHours(72));
        await Assert.That(data.MoneyCost).IsEqualTo(0L);

        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT COUNT(*)
            FROM items i
            JOIN item_categories c ON c.id = i.category_id
            LEFT JOIN item_secure_exceptions e ON e.item_id = i.id
            WHERE lower(CAST(c.secure AS TEXT)) IN ('t', 'true', '1')
              AND e.item_id IS NULL
            """;
        var eligibleCount = Convert.ToInt32(await command.ExecuteScalarAsync());
        await Assert.That(eligibleCount).IsEqualTo(9915);
    }

    public void Dispose()
    {
        _connection.Dispose();
        GC.SuppressFinalize(this);
    }
}
