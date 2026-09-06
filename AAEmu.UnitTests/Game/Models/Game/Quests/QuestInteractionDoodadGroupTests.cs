using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestInteractionDoodadGroupTests
{
    [Test]
    public async Task NativeGroupObjective_AcceptsEveryMemberAndRejectsUnrelatedOrZeroDoodads()
    {
        using var connection = new SqliteConnection("Data Source=:memory:");
        connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            CREATE TABLE quest_doodads (quest_doodad_group_id INTEGER, doodad_id INTEGER);
            INSERT INTO quest_doodads VALUES (17,16716),(17,16719),(17,16720),(18,99);
            """;
        command.ExecuteNonQuery();
        var groups = QuestDoodadGroupCatalog.Load(connection);
        var objective = new QuestActObjInteraction(new QuestComponentTemplate(null))
        {
            DoodadId = 0, DoodadGroupId = 17, DoodadGroupMembers = groups[17]
        };
        foreach (var id in new uint[] { 16716, 16719, 16720 })
            await Assert.That(objective.MatchesDoodad(id)).IsTrue();
        foreach (var id in new uint[] { 0, 99, 13319 })
            await Assert.That(objective.MatchesDoodad(id)).IsFalse();
    }

    [Test]
    public async Task MissingGroup_DoesNotCreditAnyInteraction()
    {
        var objective = new QuestActObjInteraction(new QuestComponentTemplate(null)) { DoodadGroupId = 999 };
        await Assert.That(objective.MatchesDoodad(16716)).IsFalse();
        await Assert.That(objective.MatchesDoodad(0)).IsFalse();
    }

    [Test]
    public async Task IndividualObjective_RetainsExactTemplateMatching()
    {
        var objective = new QuestActObjInteraction(new QuestComponentTemplate(null)) { DoodadId = 13319 };
        await Assert.That(objective.MatchesDoodad(13319)).IsTrue();
        await Assert.That(objective.MatchesDoodad(16716)).IsFalse();
        await Assert.That(objective.MatchesDoodad(0)).IsFalse();
    }
}
