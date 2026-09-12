using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game.Char;

public class CharacterGardenScore(Character owner)
{
    private readonly object _sync = new();
    private int _score;
    public int Score { get { lock (_sync) return _score; } }
    public int Level => GardenScoreGameData.Instance.GetLevel(Score);

    public void Add(int delta)
    {
        lock (_sync)
        {
            var data = GardenScoreGameData.Instance;
            if (owner.Quests?.ActiveQuests.ContainsKey(data.QuestId) != true) return;
            var next = GardenScoreGameData.ApplyDelta(_score, GardenScoreRate.ScaleGain(delta), data.Maximum);
            var applied = next - _score;
            if (applied == 0) return;
            _score = next;
            owner.SendPacket(new SCZoneScoreUpdatePacket((int)GardenScoreGameData.Kind, unchecked((uint)applied)));
        }
    }

    public void ResetForQuest(uint questId)
    {
        if (questId != GardenScoreGameData.Instance.QuestId) return;
        lock (_sync)
        {
            _score = 0;
            owner.SendPacket(new SCZoneScoreResetPacket((int)GardenScoreGameData.Kind));
        }
    }

    public void SendState()
    {
        lock (_sync)
        {
            owner.SendPacket(new SCZoneScoreResetPacket((int)GardenScoreGameData.Kind));
            if (_score != 0) owner.SendPacket(new SCZoneScoreUpdatePacket((int)GardenScoreGameData.Kind, (uint)_score));
        }
    }

    public void Load(MySqlConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT score FROM character_zone_scores WHERE owner=@owner AND kind=3";
        command.Parameters.AddWithValue("@owner", owner.Id);
        var value = command.ExecuteScalar();
        lock (_sync) _score = owner.Quests?.ActiveQuests.ContainsKey(GardenScoreGameData.Instance.QuestId) == true && value != null
            ? GardenScoreGameData.ApplyDelta(0, Convert.ToInt32(value), GardenScoreGameData.Instance.Maximum) : 0;
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        lock (_sync)
        {
            using var command = connection.CreateCommand(); command.Transaction = transaction;
            command.CommandText = "INSERT INTO character_zone_scores(owner,kind,score) VALUES(@owner,3,@score) ON DUPLICATE KEY UPDATE score=@score";
            command.Parameters.AddWithValue("@owner", owner.Id); command.Parameters.AddWithValue("@score", _score);
            command.ExecuteNonQuery();
        }
    }
}
