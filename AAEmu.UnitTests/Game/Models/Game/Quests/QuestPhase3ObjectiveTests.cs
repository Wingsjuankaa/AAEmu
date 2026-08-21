using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Utils.DB;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class QuestPhase3ObjectiveTests
{
    [Test]
    public async Task NpcKill_UsesInclusiveOpenEndedRangesAndNativeGradeBits()
    {
        const int normalEliteStrong = 67;
        await Assert.That(QuestActObjNpcKill.MatchesVictim(10, 0, 1, 10, 0, 0, 55, normalEliteStrong)).IsTrue();
        await Assert.That(QuestActObjNpcKill.MatchesVictim(99, 0, 7, 10, 0, 0, 55, normalEliteStrong)).IsTrue();
        await Assert.That(QuestActObjNpcKill.MatchesVictim(9, 0, 1, 10, 0, 0, 55, normalEliteStrong)).IsFalse();
        await Assert.That(QuestActObjNpcKill.MatchesVictim(10, 0, 3, 10, 0, 0, 55, normalEliteStrong)).IsFalse();
    }

    [Test]
    public async Task PcKill_LevelGapRejectsOnlyVictimsTooFarBelowKiller()
    {
        await Assert.That(QuestActObjPcKill.MatchesLevelGap(50, 46, 4)).IsTrue();
        await Assert.That(QuestActObjPcKill.MatchesLevelGap(50, 45, 4)).IsFalse();
        await Assert.That(QuestActObjPcKill.MatchesLevelGap(50, 55, 4)).IsTrue();
    }

    [Test]
    public async Task BackpackContent_SupportsExactItemsAndAa10Tags()
    {
        static IReadOnlySet<uint> Tags(uint tagId) => tagId == 91 ? new HashSet<uint> { 500, 501 } : new HashSet<uint>();
        await Assert.That(QuestActObjSellBackpackGood.MatchesContent("Item", 500, 500, Tags)).IsTrue();
        await Assert.That(QuestActObjSellBackpackGood.MatchesContent("Item", 500, 501, Tags)).IsFalse();
        await Assert.That(QuestActObjSellBackpackGood.MatchesContent("Tag", 91, 501, Tags)).IsTrue();
        await Assert.That(QuestActObjSellBackpackGood.MatchesContent("Unknown", 91, 501, Tags)).IsFalse();
    }

    [Test]
    public async Task SendMail_RequiresEveryConfiguredAttachmentAmount()
    {
        IReadOnlyDictionary<uint, int> items = new Dictionary<uint, int> { [100] = 2, [200] = 1 };
        await Assert.That(QuestActObjSendMail.ContainsRequirements(items, (100, 2), (200, 1), (0, 0))).IsTrue();
        await Assert.That(QuestActObjSendMail.ContainsRequirements(items, (100, 3))).IsFalse();
        await Assert.That(QuestActObjSendMail.ContainsRequirements(items, (300, 1))).IsFalse();
    }

    [Test]
    public async Task Phase3ObjectiveTypes_AreConcreteQuestTemplates()
    {
        var expected = new HashSet<string>
        {
            "QuestActObjCompleteQuestGroup", "QuestActObjConquestWar", "QuestActObjConsumeEvolvingMaterial",
            "QuestActObjEnchantScaleCount", "QuestActObjFactionCompetition", "QuestActObjGainExpPoint",
            "QuestActObjGainHonorPoint", "QuestActObjGainLivingPoint", "QuestActObjInviteTeamFaction",
            "QuestActObjMonsterContrGroupHunt", "QuestActObjMonsterContrHunt", "QuestActObjNpcKill",
            "QuestActObjPcKill", "QuestActObjSellBackpackGood"
        };
        var actual = typeof(QuestActObjPhase3Event).Assembly.GetTypes()
            .Where(type => !type.IsAbstract && type.IsSubclassOf(typeof(QuestActTemplate)))
            .Select(type => type.Name).ToHashSet();
        await Assert.That(expected.IsSubsetOf(actual)).IsTrue();
    }

    [Test]
    public async Task GainPointLoader_UsesRetailIdAndPointSchemaWithoutAliasColumns()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using (var create = connection.CreateCommand())
        {
            create.CommandText = "CREATE TABLE point_rows (id INTEGER PRIMARY KEY, point INTEGER NOT NULL); " +
                                 "INSERT INTO point_rows VALUES (1, 125);";
            await create.ExecuteNonQueryAsync();
        }

        await using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM point_rows";
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        await Assert.That(reader.Read()).IsTrue();
        var parent = new QuestComponentTemplate(new QuestTemplate());
        var template = QuestManager.ReadPointObjective(reader, new QuestActObjGainExpPoint(parent));

        await Assert.That(template.Count).IsEqualTo(125);
        await Assert.That(template.UseAlias).IsFalse();
        await Assert.That(template.QuestActObjAliasId).IsEqualTo(0u);
    }
}
