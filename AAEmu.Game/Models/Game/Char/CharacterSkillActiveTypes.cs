using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Heirs;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Utils.DB;

using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Models.Game.Char
{
    public sealed class CharacterSkillActiveTypes
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly object _sync = new object();
        private readonly Dictionary<(uint Heir, uint Skill), SkillActiveType> _states =
            new Dictionary<(uint Heir, uint Skill), SkillActiveType>();
        private readonly Character _owner;

        public CharacterSkillActiveTypes(Character owner) { _owner = owner; }

        public SkillActiveType GetHeirState(uint heirSkillId, HeirSkillDetail detail)
        {
            lock (_sync)
            {
                return _states.TryGetValue((heirSkillId, detail.SkillId), out var state)
                    ? state : detail.SkillActiveTypeId;
            }
        }

        public bool TrySet(uint heirSkillType, uint skillType, SkillActiveType activeType, bool notify = true)
        {
            if (!Enum.IsDefined(typeof(SkillActiveType), activeType) ||
                !IsValidPair(heirSkillType, skillType))
                return false;
            lock (_sync)
            {
                var key = (heirSkillType, skillType);
                if (!_states.ContainsKey(key) && _states.Count >= SCListSkillActiveTypsPacket.MaxEntries)
                    return false;
                if (!TryPersistState(heirSkillType, skillType, activeType))
                    return false;
                _states[key] = activeType;
                if (notify)
                    _owner.SendPacket(new SCUpdateSkillActiveTypePacket(ToEntry(key, activeType)));
                return true;
            }
        }

        public IReadOnlyList<SkillActiveTypeEntry> BuildPacketEntries()
        {
            lock (_sync)
            {
                // SCListSkillActiveTyps is the client's effective-state snapshot, not merely a
                // persistence delta. Sending only _states makes a fresh AA8 character receive an
                // empty list and leaves otherwise selectable Heir variants disabled in the UI.
                var effective = new Dictionary<(uint Heir, uint Skill), SkillActiveType>();
                var step = HeirGameData.Instance.GetStepForLevel(_owner.HierLevel);
                foreach (var heir in HeirGameData.Instance.GetSelectableHeirSkillsForStep(step))
                {
                    foreach (var detail in heir.Successors)
                    {
                        var key = (heir.Id, detail.SkillId);
                        effective[key] = _states.TryGetValue(key, out var persisted)
                            ? persisted
                            : detail.SkillActiveTypeId;
                    }
                }

                // Generic active-type transitions use heir 0 and have no static Heir row.
                foreach (var pair in _states.Where(pair => pair.Key.Heir == 0))
                    effective[pair.Key] = pair.Value;

                var entries = effective
                    .OrderBy(pair => pair.Key.Heir)
                    .ThenBy(pair => pair.Key.Skill)
                    .Select(pair => ToEntry(pair.Key, pair.Value))
                    .ToArray();
                if (entries.Length <= SCListSkillActiveTypsPacket.MaxEntries)
                    return entries;

                Log.Error(
                    "AA8 effective skill active-type list exceeds native limit: owner={0}, count={1}, limit={2}",
                    _owner.Id, entries.Length, SCListSkillActiveTypsPacket.MaxEntries);
                return entries.Take(SCListSkillActiveTypsPacket.MaxEntries).ToArray();
            }
        }

        public void Load(MySqlConnection connection)
        {
            lock (_sync) _states.Clear();
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT heir_skill_type,skill_type,active_type " +
                                      "FROM character_skill_active_types WHERE owner=@owner";
                command.Parameters.AddWithValue("@owner", _owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var heir = reader.GetUInt32("heir_skill_type");
                        var skill = reader.GetUInt32("skill_type");
                        var state = (SkillActiveType)reader.GetByte("active_type");
                        if (Enum.IsDefined(typeof(SkillActiveType), state) && IsValidPair(heir, skill))
                        {
                            lock (_sync)
                            {
                                if (_states.Count < SCListSkillActiveTypsPacket.MaxEntries)
                                    _states[(heir, skill)] = state;
                            }
                        }
                        else
                            Log.Warn("Ignoring invalid skill active type: owner={0}, heir={1}, skill={2}, active={3}",
                                _owner.Id, heir, skill, (byte)state);
                    }
                }
            }
        }

        public void Save(MySqlConnection connection, MySqlTransaction transaction)
        {
            lock (_sync)
            {
                using (var delete = connection.CreateCommand())
                {
                    delete.Transaction = transaction;
                    delete.CommandText = "DELETE FROM character_skill_active_types WHERE owner=@owner";
                    delete.Parameters.AddWithValue("@owner", _owner.Id);
                    delete.ExecuteNonQuery();
                }
                foreach (var pair in _states)
                {
                    using (var insert = connection.CreateCommand())
                    {
                        insert.Transaction = transaction;
                        insert.CommandText = "INSERT INTO character_skill_active_types" +
                            "(owner,heir_skill_type,skill_type,active_type) VALUES(@owner,@heir,@skill,@active)";
                        insert.Parameters.AddWithValue("@owner", _owner.Id);
                        insert.Parameters.AddWithValue("@heir", pair.Key.Heir);
                        insert.Parameters.AddWithValue("@skill", pair.Key.Skill);
                        insert.Parameters.AddWithValue("@active", (byte)pair.Value);
                        insert.ExecuteNonQuery();
                    }
                }
            }
        }

        private bool TryPersistState(uint heirSkillType, uint skillType, SkillActiveType activeType)
        {
            try
            {
                using (var connection = MySQL.CreateConnection())
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "INSERT INTO character_skill_active_types" +
                        "(owner,heir_skill_type,skill_type,active_type) VALUES(@owner,@heir,@skill,@active) " +
                        "ON DUPLICATE KEY UPDATE active_type=VALUES(active_type)";
                    command.Parameters.AddWithValue("@owner", _owner.Id);
                    command.Parameters.AddWithValue("@heir", heirSkillType);
                    command.Parameters.AddWithValue("@skill", skillType);
                    command.Parameters.AddWithValue("@active", (byte)activeType);
                    command.ExecuteNonQuery();
                    return true;
                }
            }
            catch (Exception exception)
            {
                Log.Error(exception,
                    "Failed to persist skill active type: owner={0}, heir={1}, skill={2}, active={3}",
                    _owner.Id, heirSkillType, skillType, (byte)activeType);
                return false;
            }
        }

        private static SkillActiveTypeEntry ToEntry((uint Heir, uint Skill) key, SkillActiveType state)
        {
            return new SkillActiveTypeEntry
            {
                HeirSkillType = checked((int)key.Heir),
                SkillType = checked((int)key.Skill),
                ActiveType = (byte)state
            };
        }

        private static bool IsValidPair(uint heirSkillType, uint skillType)
        {
            if (skillType == 0) return false;
            if (heirSkillType == 0)
                return SkillManager.Instance.GetSkillTemplate(skillType) != null;
            return HeirGameData.Instance.TryGetHeirSkillForSuccessor(
                skillType, out var owner, out _) && owner.Id == heirSkillType;
        }
    }
}
