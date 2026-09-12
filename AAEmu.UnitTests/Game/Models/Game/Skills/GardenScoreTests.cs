using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using Microsoft.Data.Sqlite;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Zones;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class GardenScoreTests
{
    [Test]
    [Arguments(ZoneConflictType.Tension, 0u, 0u, true)]
    [Arguments(ZoneConflictType.War, 0u, 1u, true)]
    [Arguments(ZoneConflictType.Peace, 0u, 1u, true)]
    [Arguments(ZoneConflictType.Peace, 1u, 0u, true)]
    [Arguments(ZoneConflictType.Tension, 1u, 0u, false)]
    [Arguments(ZoneConflictType.War, 1u, 0u, false)]
    [Arguments(ZoneConflictType.War, 2u, 0u, true)]
    [Arguments(ZoneConflictType.Peace, 2u, 0u, false)]
    [Arguments(null, 1u, 0u, false)]
    [Arguments(ZoneConflictType.Peace, 3u, 0u, false)]
    public async Task ConflictGate_UsesNativePredicates(ZoneConflictType? state, uint mode, uint expected, bool result)
        => await Assert.That(UnitReqs.MatchesConflictState(state, mode, expected)).IsEqualTo(result);

    [Test]
    [NotInParallel]
    public async Task ScoreRequiresQuest_AndResetsOnlyWithItsOwnQuest()
    {
        using var connection = new SqliteConnection("Data Source=:memory:"); connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "CREATE TABLE zone_score_contents(id,zone_group_id,quest_id);" +
            "CREATE TABLE zone_score_kinds(id,content_id,max_score,db_save);" +
            "CREATE TABLE zone_score_levels(kind_id,level,req_score);" +
            "INSERT INTO zone_score_contents VALUES(2,133,10056);" +
            "INSERT INTO zone_score_kinds VALUES(3,2,10064800,'t');" +
            "INSERT INTO zone_score_levels VALUES(3,0,0),(3,1,2500);";
        command.ExecuteNonQuery();
        GardenScoreGameData.Instance.Load(connection);
        var owner = new Character(null);
        owner.Quests = new CharacterQuests(owner);
        owner.GardenScore.Add(75);
        await Assert.That(owner.GardenScore.Score).IsEqualTo(0);
        owner.Quests.ActiveQuests.Add(10056, null);
        Parallel.For(0, 100, _ => owner.GardenScore.Add(75));
        await Assert.That(owner.GardenScore.Score).IsEqualTo(7500);
        owner.GardenScore.ResetForQuest(10055);
        await Assert.That(owner.GardenScore.Score).IsEqualTo(7500);
        owner.GardenScore.ResetForQuest(10056);
        await Assert.That(owner.GardenScore.Score).IsEqualTo(0);
    }

    [Test]
    [Arguments(0, 75, 75)]
    [Arguments(2499, 75, 2574)]
    [Arguments(500, -2500, 0)]
    [Arguments(10064800, 75, 10064800)]
    [Arguments(10064800, int.MaxValue, 10064800)]
    public async Task PointDeltas_ClampWithoutOverflow(int before, int delta, int expected)
    {
        await Assert.That(GardenScoreGameData.ApplyDelta(before, delta, 10064800)).IsEqualTo(expected);
    }

    [Test]
    public async Task Catalog_UsesCumulativeLevelThresholds()
    {
        using var connection = new SqliteConnection("Data Source=:memory:"); connection.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "CREATE TABLE zone_score_contents(id INTEGER,zone_group_id INTEGER,quest_id INTEGER);" +
            "CREATE TABLE zone_score_kinds(id INTEGER,content_id INTEGER,max_score INTEGER,db_save TEXT);" +
            "CREATE TABLE zone_score_levels(kind_id INTEGER,level INTEGER,req_score INTEGER);" +
            "INSERT INTO zone_score_contents VALUES(2,133,10056);" +
            "INSERT INTO zone_score_kinds VALUES(3,2,10064800,'t');" +
            "INSERT INTO zone_score_levels VALUES(3,0,0),(3,1,2500),(3,2,5400),(3,12,64800);";
        command.ExecuteNonQuery();
        var data = new GardenScoreGameData(); data.Load(connection);
        await Assert.That(data.QuestId).IsEqualTo(10056u);
        await Assert.That(data.GetLevel(2499)).IsEqualTo(0);
        await Assert.That(data.GetLevel(2500)).IsEqualTo(1);
        await Assert.That(data.GetLevel(5400)).IsEqualTo(2);
        await Assert.That(data.GetLevel(10064800)).IsEqualTo(12);
    }

    [Test]
    public async Task SignedDelta_PreservesNativeTwosComplementBody()
    {
        var packet = new SCZoneScoreUpdatePacket(3, unchecked((uint)-2500));
        var stream = packet.Write(new PacketStream());
        await Assert.That(Convert.ToHexString(stream.GetBytes())).IsEqualTo("030000003CF6FFFF");
    }
}
