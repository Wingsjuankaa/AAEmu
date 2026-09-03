using AAEmu.Game.GameData;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.GameData;

public class LootGachaGameDataTests
{
    [Test]
    public async Task CanonicalR575Catalog_WhenAvailable_HasClosedCountsAndMappings()
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
        var data = new LootGachaGameData();
        data.Load(connection);

        await Assert.That(data.PackCount).IsEqualTo(11);
        await Assert.That(data.ItemMappingCount).IsEqualTo(24);
        await Assert.That(data.AdvancedPackCount).IsEqualTo(30);
        await Assert.That(data.TryGetActivePack(42333, 42335, out var pack)).IsTrue();
        await Assert.That(pack.Id).IsEqualTo(3u);
        await Assert.That(pack.LootPackId).IsEqualTo(10863u);
        await Assert.That(data.TryGetActivePack(53078, 0, out _)).IsFalse();
    }
}
