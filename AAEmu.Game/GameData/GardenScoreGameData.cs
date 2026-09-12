using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData;

/// <summary>r575 Garden score kind 3. Thresholds are cumulative, as in native GetZoneScore.</summary>
[GameData]
public class GardenScoreGameData : Singleton<GardenScoreGameData>, IGameDataLoader
{
    public const uint Kind = 3;
    public uint QuestId { get; private set; }
    public int Maximum { get; private set; }
    public SortedDictionary<int, int> Levels { get; } = [];
    public void Load(SqliteConnection connection)
    {
        Levels.Clear();
        using var command = connection.CreateCommand();
        // Retail booleans use 't'/'f' in some SQLite projections.
        command.CommandText = "SELECT k.max_score,c.quest_id FROM zone_score_kinds k JOIN zone_score_contents c ON c.id=k.content_id WHERE k.id=3 AND c.zone_group_id=133 AND (k.db_save=1 OR k.db_save='t')";
        using (var reader = command.ExecuteReader())
        {
            if (!reader.Read()) throw new InvalidDataException("Missing r575 Garden score contract");
            Maximum = reader.GetInt32(0); QuestId = (uint)reader.GetInt64(1);
        }
        command.CommandText = "SELECT level,req_score FROM zone_score_levels WHERE kind_id=3 ORDER BY level";
        using var levels = command.ExecuteReader();
        while (levels.Read()) Levels.Add(levels.GetInt32(0), levels.GetInt32(1));
    }
    public void PostLoad() { }
    public int GetLevel(int score) => Levels.Where(pair => score >= pair.Value).Select(pair => pair.Key).DefaultIfEmpty(0).Max();
    internal static int ApplyDelta(int current, int delta, int maximum) => (int)Math.Clamp((long)current + delta, 0, maximum);
}
