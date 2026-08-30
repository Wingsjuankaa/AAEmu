using AAEmu.Game.Core.Managers.Id;

namespace AAEmu.UnitTests.Game.Core.Managers.Id;

public class CharacterOwnerDomainTests
{
    [Test]
    public async Task CharacterAllocatorStartsInAa10LiteralHousingOwnerDomain()
    {
        var manager = new CharacterIdManager();
        manager.Initialize(true);

        await Assert.That(manager.GetNextId()).IsEqualTo(1000u);
    }

    [Test]
    public async Task LowCharacterIdMigrationIsTransactionalAndCoversPersistentReferences()
    {
        var source = await File.ReadAllTextAsync(RepositoryPath(
            "SQL", "updates", "2026-08-30_aaemu_game_character_owner_domain.sql"));

        await Assert.That(source).Contains("START TRANSACTION;");
        await Assert.That(source).Contains("WHERE `id` > 0 AND `id` < 1000");
        await Assert.That(source).Contains("`id` + 1000");
        await Assert.That(source).Contains("UPDATE `housings`");
        await Assert.That(source).Contains("t.`permission` = 0");
        await Assert.That(source).Contains("UPDATE `items`");
        await Assert.That(source).Contains("UPDATE `character_arche_passes`");
        await Assert.That(source).Contains("UPDATE `quest_reward_ledger`");
        await Assert.That(source).Contains("UPDATE `resident_service_points`");
        await Assert.That(source).Contains("UPDATE `slaves`");
        await Assert.That(source).Contains("UPDATE `characters`");
        await Assert.That(source).Contains("COMMIT;");
    }

    [Test]
    public async Task CharacterAndSlaveIdsRemainInTheSharedCollisionAudit()
    {
        var source = await File.ReadAllTextAsync(RepositoryPath(
            "AAEmu.Game", "Core", "Managers", "Id", "CharacterIdManager.cs"));

        await Assert.That(source).Contains("FirstId = 0x000003E8");
        await Assert.That(source).Contains("{ \"characters\", \"id\" }");
        await Assert.That(source).Contains("{ \"slaves\", \"id\" }");
    }

    private static string RepositoryPath(params string[] parts)
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "AAEmu.slnx")))
            directory = directory.Parent;

        if (directory is null)
            throw new DirectoryNotFoundException("Could not locate the AAEmu repository root.");

        return parts.Aggregate(directory.FullName, Path.Combine);
    }
}
