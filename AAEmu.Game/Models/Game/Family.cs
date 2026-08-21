using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game;

public class Family : PacketMarshaler
{
    private readonly List<uint> _removedMembers = [];

    public uint Id { get; init; }
    public uint Level { get; set; } = 1;
    public uint Exp { get; set; }
    public string Name { get; set; } = string.Empty;
    public int Type { get; set; }
    public uint IncMemberCount { get; set; }
    public long ChangeNameTime { get; set; }
    public List<FamilyMember> Members { get; } = [];

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(Id);
        stream.Write(Members.Count); // TODO max length 8
        foreach (var member in Members)
            stream.Write(member);
        return stream;
    }

    public void AddMember(FamilyMember member)
    {
        Members.Add(member);
    }

    public void RemoveMember(FamilyMember member)
    {
        Members.Remove(member);
        _removedMembers.Add(member.Id);
    }

    public void RemoveMember(Character character)
    {
        var member = GetMember(character);
        RemoveMember(member);
        character.Family = 0;
    }

    public FamilyMember GetMember(Character character)
    {
        foreach (var member in Members)
            if (member.Id == character.Id)
                return member;

        return null;
    }

    public void SendPacket(GamePacket packet, uint exclude = 0)
    {
        foreach (var member in Members)
            if (member.Id != exclude)
                member.Character?.SendPacket(packet);
    }

    public void Load(MySqlConnection connection)
    {
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT level, exp, name, type, inc_member_count, change_name_time FROM family_progress WHERE family_id=@family_id";
            command.Parameters.AddWithValue("@family_id", Id);
            using var reader = command.ExecuteReader();
            if (reader.Read())
            {
                Level = reader.GetUInt32("level");
                Exp = reader.GetUInt32("exp");
                Name = reader.GetString("name");
                Type = reader.GetInt32("type");
                IncMemberCount = reader.GetUInt32("inc_member_count");
                ChangeNameTime = reader.GetInt64(reader.GetOrdinal("change_name_time"));
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM family_members WHERE family_id=@family_id";
            command.Parameters.AddWithValue("family_id", Id);
            command.Prepare();
            using (var reader = command.ExecuteReader())
            {
                while (reader.Read())
                {
                    var member = new FamilyMember
                    {
                        Id = reader.GetUInt32("character_id"), Name = reader.GetString("name"), Role = reader.GetByte("role"),
                        Title = reader.GetString("title")
                    };
                    AddMember(member);
                }
            }
        }
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        if (_removedMembers.Count > 0)
        {
            var removedMembers = string.Join(",", _removedMembers);

            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = $"DELETE FROM family_members WHERE character_id IN ({removedMembers})";
                command.Parameters.AddWithValue("@family_id", Id);
                command.Prepare();
                command.ExecuteNonQuery();
            }

            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = $"UPDATE characters SET family = 0 WHERE `characters`.`id` IN ({removedMembers})";
                command.Parameters.AddWithValue("@family_id", Id);
                command.Prepare();
                command.ExecuteNonQuery();
            }

            _removedMembers.Clear();
        }

        using (var command = connection.CreateCommand())
        {
            command.Connection = connection;
            command.Transaction = transaction;
            foreach (var member in Members)
            {
                command.CommandText = "REPLACE INTO " +
                                      "family_members(`character_id`,`family_id`,`name`,`role`,`title`)" +
                                      " VALUES " +
                                      "(@character_id,@family_id,@name,@role,@title)";
                command.Parameters.AddWithValue("@character_id", member.Id);
                command.Parameters.AddWithValue("@family_id", Id);
                command.Parameters.AddWithValue("@name", member.Name);
                command.Parameters.AddWithValue("@role", member.Role);
                command.Parameters.AddWithValue("@title", member.Title);
                command.ExecuteNonQuery();
                command.Parameters.Clear();
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.Transaction = transaction;
            if (Members.Count == 0)
            {
                command.CommandText = "DELETE FROM family_progress WHERE family_id=@family_id";
                command.Parameters.AddWithValue("@family_id", Id);
            }
            else
            {
                command.CommandText = @"INSERT INTO family_progress
(family_id, level, exp, name, type, inc_member_count, change_name_time)
VALUES (@family_id, @level, @exp, @name, @type, @inc_member_count, @change_name_time)
ON DUPLICATE KEY UPDATE level=VALUES(level), exp=VALUES(exp), name=VALUES(name),
type=VALUES(type), inc_member_count=VALUES(inc_member_count), change_name_time=VALUES(change_name_time)";
                command.Parameters.AddWithValue("@family_id", Id);
                command.Parameters.AddWithValue("@level", Level);
                command.Parameters.AddWithValue("@exp", Exp);
                command.Parameters.AddWithValue("@name", Name);
                command.Parameters.AddWithValue("@type", Type);
                command.Parameters.AddWithValue("@inc_member_count", IncMemberCount);
                command.Parameters.AddWithValue("@change_name_time", ChangeNameTime);
            }
            command.ExecuteNonQuery();
        }
    }
}

public class FamilyMember : PacketMarshaler
{
    public Character Character { get; set; }

    public uint Id { get; set; }
    public string Name { get; set; }
    public byte Role { get; set; }
    public bool Online => Character != null;
    public string Title { get; set; }

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(Id);
        stream.Write(Name);
        stream.Write(Role);
        stream.Write(Online);
        stream.Write(Title);
        return stream;
    }
}
