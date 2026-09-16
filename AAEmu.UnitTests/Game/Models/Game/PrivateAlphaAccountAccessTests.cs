using AAEmu.Game.Models.Game.PrivateAlpha;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game;

public class PrivateAlphaAccountAccessTests
{
    private static SqliteConnection CreateDatabase()
    {
        var db = new SqliteConnection("Data Source=:memory:");
        db.Open();
        Execute(db, """
            CREATE TABLE characters (id INTEGER PRIMARY KEY, account_id INTEGER, deleted INTEGER);
            CREATE TABLE private_alpha_access (character_id INTEGER PRIMARY KEY);
            CREATE TABLE private_alpha_account_access (account_id INTEGER PRIMARY KEY);
            INSERT INTO characters VALUES (101,5,0),(102,5,0),(103,9,0),(104,5,1);
            INSERT INTO private_alpha_account_access VALUES (5);
            """);
        return db;
    }

    private static void Execute(SqliteConnection db, string sql)
    {
        using var command = db.CreateCommand();
        command.CommandText = sql;
        command.ExecuteNonQuery();
    }

    private static bool HasAccess(SqliteConnection db, uint id)
    {
        using var command = db.CreateCommand();
        command.CommandText = AlphaRepository.AccessQuery;
        command.Parameters.AddWithValue("@id", id);
        return command.ExecuteScalar() is not null;
    }

    [Test]
    public async Task AccountGrantCoversExistingAndFutureCharactersButNotOtherAccountsOrDeletedCharacters()
    {
        using var db = CreateDatabase();
        await Assert.That(HasAccess(db, 101)).IsTrue();
        await Assert.That(HasAccess(db, 102)).IsTrue();
        await Assert.That(HasAccess(db, 103)).IsFalse();
        await Assert.That(HasAccess(db, 104)).IsFalse();
        await Assert.That(HasAccess(db, 105)).IsFalse();
        Execute(db, "INSERT INTO characters VALUES (105,5,0)");
        await Assert.That(HasAccess(db, 105)).IsTrue();
    }

    [Test]
    public async Task AccountRevocationRemovesInheritedAccessAndPreservesExplicitCharacterGrants()
    {
        using var db = CreateDatabase();
        Execute(db, "INSERT INTO private_alpha_access VALUES (102),(103); DELETE FROM private_alpha_account_access WHERE account_id=5");
        await Assert.That(HasAccess(db, 101)).IsFalse();
        await Assert.That(HasAccess(db, 102)).IsTrue();
        await Assert.That(HasAccess(db, 103)).IsTrue();
        Execute(db, "INSERT INTO characters VALUES (105,5,0)");
        await Assert.That(HasAccess(db, 105)).IsFalse();
    }

    [Test]
    public async Task IndividualRevocationPreservesAccountAccessAndOwnershipChangesTakeEffectImmediately()
    {
        using var db = CreateDatabase();
        Execute(db, "INSERT INTO private_alpha_access VALUES (101); DELETE FROM private_alpha_access WHERE character_id=101");
        await Assert.That(HasAccess(db, 101)).IsTrue();
        Execute(db, "UPDATE characters SET account_id=9 WHERE id=101");
        await Assert.That(HasAccess(db, 101)).IsFalse();
    }
}
