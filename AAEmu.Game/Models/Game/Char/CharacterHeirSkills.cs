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
    public sealed class CharacterHeirSkills
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();
        private readonly object _sync = new object();
        private readonly Dictionary<uint, uint> _active = new Dictionary<uint, uint>();
        private readonly Character _owner;

        public CharacterHeirSkills(Character owner) { _owner = owner; }

        public bool TryActivate(uint heirSkillId, uint successorSkillId, bool isChange)
        {
            if (!TryResolve(heirSkillId, successorSkillId, out var heir, out var detail, out _))
                return false;
            if (_owner.SkillActiveTypes.GetHeirState(heirSkillId, detail) != SkillActiveType.Active)
                return false;
            lock (_sync)
            {
                var hasCurrent = _active.TryGetValue(heirSkillId, out var current);
                if (!IsValidActivationTransition(hasCurrent, current, successorSkillId, isChange) ||
                    !TryPersistSelection(heirSkillId, successorSkillId))
                    return false;
                _active[heirSkillId] = successorSkillId;
                _owner.SendPacket(new SCActivatedHeirSkillPacket(
                    checked((int)heir.Id), checked((int)successorSkillId), isChange));
                return true;
            }
        }

        public bool TryReset(HeirSkillResetKind kind, sbyte ability, int successorSkillId)
        {
            lock (_sync)
            {
                List<uint> removals;
                if (kind == HeirSkillResetKind.All)
                    removals = _active.Keys.ToList();
                else if (kind == HeirSkillResetKind.Ability && IsValidAbility(ability))
                    removals = _active.Where(pair =>
                        SkillManager.Instance.GetSkillTemplate(pair.Value)?.AbilityId == (byte)ability)
                        .Select(pair => pair.Key).ToList();
                else if (kind == HeirSkillResetKind.Successor && successorSkillId > 0)
                    removals = _active.Where(pair => pair.Value == (uint)successorSkillId)
                        .Select(pair => pair.Key).Take(1).ToList();
                else
                    return false;

                if (removals.Count == 0 || !TryDeletePersistedSelections(removals))
                    return false;
                foreach (var key in removals) _active.Remove(key);
                _owner.SendPacket(new SCResetHeirSkillPacket((uint)kind, successorSkillId, ability));
                return true;
            }
        }

        public bool RemoveByAbility(AbilityType ability)
        {
            return TryReset(HeirSkillResetKind.Ability, checked((sbyte)ability), 0);
        }

        public bool IsActiveSuccessor(uint skillId)
        {
            lock (_sync)
            {
                var match = _active.FirstOrDefault(pair => pair.Value == skillId);
                if (match.Key == 0 ||
                    !HeirGameData.Instance.TryGetHeirSkillForSuccessor(skillId, out var heir, out var detail))
                    return false;
                return heir.Id == match.Key &&
                       _owner.SkillActiveTypes.GetHeirState(heir.Id, detail) == SkillActiveType.Active;
            }
        }

        public IReadOnlyList<HeirSkillListEntry> BuildPacketEntries()
        {
            KeyValuePair<uint, uint>[] snapshot;
            lock (_sync) snapshot = _active.OrderBy(value => value.Key).ToArray();
            var result = new List<HeirSkillListEntry>();
            foreach (var pair in snapshot)
            {
                if (!TryResolve(pair.Key, pair.Value, out var heir, out var detail, out var template))
                    continue;
                result.Add(new HeirSkillListEntry
                {
                    HeirSkillId = checked((int)heir.Id), BaseSkillId = checked((int)heir.SkillId),
                    SuccessorSkillId = checked((int)detail.SkillId),
                    SkillLevel = new Skill(template, _owner).Level,
                    Ability = checked((sbyte)template.AbilityId),
                    ActiveType = checked((sbyte)_owner.SkillActiveTypes.GetHeirState(heir.Id, detail))
                });
            }
            return result;
        }

        public void Load(MySqlConnection connection)
        {
            lock (_sync) _active.Clear();
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT heir_skill_id,successor_skill_id " +
                                      "FROM heir_skill_activations WHERE owner=@owner";
                command.Parameters.AddWithValue("@owner", _owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var heir = reader.GetUInt32("heir_skill_id");
                        var successor = reader.GetUInt32("successor_skill_id");
                        if (TryResolve(heir, successor, out _, out _, out _))
                        {
                            lock (_sync) _active[heir] = successor;
                        }
                        else
                            Log.Warn("Ignoring invalid persisted Heir selection: owner={0}, heir={1}, successor={2}",
                                _owner.Id, heir, successor);
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
                    delete.CommandText = "DELETE FROM heir_skill_activations WHERE owner=@owner";
                    delete.Parameters.AddWithValue("@owner", _owner.Id);
                    delete.ExecuteNonQuery();
                }
                foreach (var pair in _active)
                {
                    using (var insert = connection.CreateCommand())
                    {
                        insert.Transaction = transaction;
                        insert.CommandText = "INSERT INTO heir_skill_activations" +
                            "(owner,heir_skill_id,successor_skill_id) VALUES(@owner,@heir,@successor)";
                        insert.Parameters.AddWithValue("@owner", _owner.Id);
                        insert.Parameters.AddWithValue("@heir", pair.Key);
                        insert.Parameters.AddWithValue("@successor", pair.Value);
                        insert.ExecuteNonQuery();
                    }
                }
            }
        }

        private static bool IsValidActivationTransition(
            bool hasCurrent, uint current, uint successorSkillId, bool isChange)
        {
            return hasCurrent == isChange && (!hasCurrent || current != successorSkillId);
        }

        private static bool IsValidAbility(sbyte ability)
        {
            return ability > (sbyte)AbilityType.General && ability < (sbyte)AbilityType.None;
        }

        private bool TryPersistSelection(uint heirSkillId, uint successorSkillId)
        {
            try
            {
                using (var connection = MySQL.CreateConnection())
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "INSERT INTO heir_skill_activations" +
                        "(owner,heir_skill_id,successor_skill_id) VALUES(@owner,@heir,@successor) " +
                        "ON DUPLICATE KEY UPDATE successor_skill_id=VALUES(successor_skill_id)";
                    command.Parameters.AddWithValue("@owner", _owner.Id);
                    command.Parameters.AddWithValue("@heir", heirSkillId);
                    command.Parameters.AddWithValue("@successor", successorSkillId);
                    command.ExecuteNonQuery();
                    return true;
                }
            }
            catch (Exception exception)
            {
                Log.Error(exception,
                    "Failed to persist Heir selection: owner={0}, heir={1}, successor={2}",
                    _owner.Id, heirSkillId, successorSkillId);
                return false;
            }
        }

        private bool TryDeletePersistedSelections(IReadOnlyCollection<uint> heirSkillIds)
        {
            try
            {
                using (var connection = MySQL.CreateConnection())
                using (var transaction = connection.BeginTransaction())
                {
                    foreach (var heirSkillId in heirSkillIds)
                    {
                        using (var command = connection.CreateCommand())
                        {
                            command.Transaction = transaction;
                            command.CommandText = "DELETE FROM heir_skill_activations " +
                                                  "WHERE owner=@owner AND heir_skill_id=@heir";
                            command.Parameters.AddWithValue("@owner", _owner.Id);
                            command.Parameters.AddWithValue("@heir", heirSkillId);
                            command.ExecuteNonQuery();
                        }
                    }
                    transaction.Commit();
                    return true;
                }
            }
            catch (Exception exception)
            {
                Log.Error(exception, "Failed to persist Heir reset: owner={0}", _owner.Id);
                return false;
            }
        }

        private bool TryResolve(uint heirSkillId, uint successorSkillId, out HeirSkill heir,
            out HeirSkillDetail detail,
            out AAEmu.Game.Models.Game.Skills.Templates.SkillTemplate successorTemplate)
        {
            var step = HeirGameData.Instance.GetStepForLevel(_owner.HierLevel);
            heir = null;
            detail = null;
            successorTemplate = null;
            if (!HeirGameData.Instance.TryGetSelectableHeirSkill(heirSkillId, step, out heir) ||
                !HeirGameData.Instance.TryGetSelectableSuccessor(
                    heirSkillId, successorSkillId, step, out detail) ||
                !_owner.Skills.Skills.ContainsKey(heir.SkillId)) return false;
            var baseTemplate = SkillManager.Instance.GetSkillTemplate(heir.SkillId);
            successorTemplate = SkillManager.Instance.GetSkillTemplate(successorSkillId);
            return baseTemplate != null && successorTemplate != null &&
                   baseTemplate.AbilityId == successorTemplate.AbilityId;
        }
    }
}
