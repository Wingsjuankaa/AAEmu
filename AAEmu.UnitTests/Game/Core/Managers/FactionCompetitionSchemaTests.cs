using AAEmu.Game.Core.Managers;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class FactionCompetitionSchemaTests
{
    [Test]
    public async Task RetailQuestRelationUsesContextId()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE faction_competition_quest_infos (
                id INTEGER PRIMARY KEY,
                faction_competition_id INTEGER NOT NULL,
                context_id INTEGER DEFAULT 0
            );
            INSERT INTO faction_competition_quest_infos VALUES (1, 5, 9398);
            """;
        await command.ExecuteNonQueryAsync();

        var relations = FactionCompetitionManager.ReadCompetitionQuestRelations(connection);

        await Assert.That(relations).Count().IsEqualTo(1);
        await Assert.That(relations[0].CompetitionId).IsEqualTo(5u);
        await Assert.That(relations[0].ContextId).IsEqualTo(9398u);
    }
}
