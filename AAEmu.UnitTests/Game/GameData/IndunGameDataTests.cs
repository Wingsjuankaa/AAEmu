using AAEmu.Game.GameData;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.GameData;

public sealed class IndunGameDataTests : IDisposable
{
    private readonly SqliteConnection _connection = new("Data Source=:memory:");

    public IndunGameDataTests()
    {
        _connection.Open();
        using var command = _connection.CreateCommand();
        command.CommandText = @"
            CREATE TABLE instances (id INTEGER PRIMARY KEY, target_id INTEGER, target_type TEXT);
            INSERT INTO instances VALUES
                (20, 51, 'IndunZone'),
                (23, 58, 'IndunZone'),
                (99, 51, 'BattleField');";
        command.ExecuteNonQuery();
    }

    [Test]
    public async Task LoadInstanceCatalogIds_MapsUnifiedIdByIndunZoneTarget()
    {
        var result = IndunGameData.LoadInstanceCatalogIds(_connection);

        await Assert.That(result.Count).IsEqualTo(2);
        await Assert.That(result[51]).IsEqualTo((uint)20);
        await Assert.That(result[58]).IsEqualTo((uint)23);
    }

    [Test]
    public async Task CanonicalR575Catalog_WhenAvailable_MapsHowlingAbyssToInstance20()
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

        var result = IndunGameData.LoadInstanceCatalogIds(connection);

        await Assert.That(result[51]).IsEqualTo((uint)20);
    }

    public void Dispose()
    {
        _connection.Dispose();
        GC.SuppressFinalize(this);
    }
}
