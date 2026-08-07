using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Utils;
using AAEmu.Game.GameData.Framework;
using AAEmu.Game.Models.Game.Heirs;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

namespace AAEmu.Game.GameData
{
    /// <summary>
    /// Exact AA8 heir progression and successor graph decoded from game11.
    /// </summary>
    [GameData]
    public sealed class HeirGameData : Singleton<HeirGameData>, IGameDataLoader
    {
        private List<HeirLevel> _levels = new List<HeirLevel>();
        private Dictionary<uint, HeirSkill> _skillsById = new Dictionary<uint, HeirSkill>();
        private Dictionary<uint, HeirSkillDetail> _successorsBySkillId =
            new Dictionary<uint, HeirSkillDetail>();

        public byte MaxLevel => _levels.Count == 0 ? (byte)0 : _levels[_levels.Count - 1].Level;
        public byte StartLevel => HeirProgressionPolicy.StartLevel;

        public byte GetLevelForExp(long totalExp)
        {
            return HeirProgressionPolicy.GetLevelForExp(_levels, totalExp);
        }

        public long ApplyExpGain(long totalExp, int expDelta)
        {
            return HeirProgressionPolicy.ApplyExpGain(_levels, totalExp, expDelta);
        }

        public bool TryGetLevelUpRequirement(
            byte characterLevel,
            long totalExp,
            out HeirLevel requirement)
        {
            return HeirProgressionPolicy.TryGetLevelUpRequirement(
                _levels, characterLevel, totalExp, out requirement);
        }

        public void Load(SqliteConnection connection)
        {
            _levels = new List<HeirLevel>();
            _skillsById = new Dictionary<uint, HeirSkill>();
            _successorsBySkillId = new Dictionary<uint, HeirSkillDetail>();
            if (!TableExists(connection, "heir_levels") ||
                !TableExists(connection, "heir_skills") ||
                !TableExists(connection, "heir_skill_details"))
                return;

            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT id,level,req_item_count,req_item_id,req_total_exp,step FROM heir_levels";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        _levels.Add(new HeirLevel
                        {
                            Id = reader.GetUInt32("id"),
                            Level = checked((byte)reader.GetUInt32("level")),
                            ReqItemCount = reader.GetInt32("req_item_count"),
                            ReqItemId = reader.GetUInt32("req_item_id"),
                            ReqTotalExp = reader.GetInt64("req_total_exp"),
                            Step = checked((byte)reader.GetUInt32("step"))
                        });
                    }
                }
            }

            var skills = new List<HeirSkill>();
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT id,skill_id,step,enable FROM heir_skills";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        skills.Add(new HeirSkill
                        {
                            Id = reader.GetUInt32("id"),
                            SkillId = reader.GetUInt32("skill_id"),
                            Step = checked((byte)reader.GetUInt32("step")),
                            Enable = reader.GetBoolean("enable", true),
                            Successors = new List<HeirSkillDetail>()
                        });
                    }
                }
            }

            var details = new List<HeirSkillDetail>();
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT id,active_item_id,desc,heir_skill_id,pos,skill_active_type_id,skill_id " +
                    "FROM heir_skill_details";
                using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                {
                    while (reader.Read())
                    {
                        details.Add(new HeirSkillDetail
                        {
                            Id = reader.GetUInt32("id"),
                            ActiveItemId = reader.GetUInt32("active_item_id"),
                            Desc = reader.GetString("desc", string.Empty),
                            HeirSkillId = reader.GetUInt32("heir_skill_id"),
                            Pos = reader.GetInt32("pos"),
                            SkillActiveTypeId = (SkillActiveType)checked(
                                (byte)reader.GetUInt32("skill_active_type_id")),
                            SkillId = reader.GetUInt32("skill_id")
                        });
                    }
                }
            }

            foreach (var skill in skills)
            {
                skill.Successors = details
                    .Where(detail => detail.HeirSkillId == skill.Id)
                    .OrderBy(detail => detail.Pos)
                    .ThenBy(detail => detail.Id)
                    .ToList();
                if (!_skillsById.TryAdd(skill.Id, skill))
                    throw new InvalidOperationException($"Duplicate AA8 heir skill id {skill.Id}");
            }
            foreach (var detail in details)
            {
                if (!_skillsById.ContainsKey(detail.HeirSkillId))
                    throw new InvalidOperationException(
                        $"AA8 heir detail {detail.Id} references missing owner {detail.HeirSkillId}");
                if (!Enum.IsDefined(typeof(SkillActiveType), detail.SkillActiveTypeId) ||
                    !_successorsBySkillId.TryAdd(detail.SkillId, detail))
                    throw new InvalidOperationException($"Invalid AA8 heir detail {detail.Id}");
            }
        }

        public void PostLoad()
        {
            _levels = _levels.OrderBy(level => level.Level).ToList();
            for (var index = 0; index < _levels.Count; index++)
            {
                if (_levels[index].Level != index)
                    throw new InvalidOperationException("AA8 heir_levels is not contiguous from zero");
                if (index > 0 && _levels[index].ReqTotalExp <= _levels[index - 1].ReqTotalExp)
                    throw new InvalidOperationException("AA8 heir experience thresholds are not increasing");
                if ((_levels[index].ReqItemId == 0 && _levels[index].ReqItemCount != 0) ||
                    (_levels[index].ReqItemId != 0 && _levels[index].ReqItemCount <= 0))
                    throw new InvalidOperationException(
                        $"AA8 heir level {_levels[index].Level} has an incomplete item requirement");
            }
        }

        public byte GetStepForLevel(byte level)
        {
            var row = _levels.FirstOrDefault(candidate => candidate.Level == level);
            return row?.Step ?? (byte)0;
        }

        public byte GetFirstLevelForStep(byte step)
        {
            var row = _levels.FirstOrDefault(candidate => candidate.Step == step);
            return row?.Level ?? (byte)0;
        }

        /// <summary>
        /// Returns the enabled AA8 Heir families visible at the supplied progression step.
        /// The returned graph is static client content; per-character overrides are applied by
        /// <see cref="Char.CharacterSkillActiveTypes"/>.
        /// </summary>
        public IReadOnlyList<HeirSkill> GetSelectableHeirSkillsForStep(byte step)
        {
            return _skillsById.Values
                .Where(skill => skill.Enable && skill.Step <= step)
                .OrderBy(skill => skill.Id)
                .ToArray();
        }

        public bool TryGetSelectableHeirSkill(uint id, byte unlockedStep, out HeirSkill skill)
        {
            return _skillsById.TryGetValue(id, out skill) &&
                   skill.Enable && skill.Step <= unlockedStep;
        }

        public bool TryGetSelectableSuccessor(
            uint heirSkillId,
            uint successorSkillId,
            byte unlockedStep,
            out HeirSkillDetail detail)
        {
            detail = null;
            return TryGetSelectableHeirSkill(heirSkillId, unlockedStep, out var owner) &&
                   _successorsBySkillId.TryGetValue(successorSkillId, out detail) &&
                   detail.HeirSkillId == owner.Id;
        }

        public bool TryGetHeirSkillForSuccessor(
            uint successorSkillId,
            out HeirSkill skill,
            out HeirSkillDetail detail)
        {
            skill = null;
            detail = null;
            return _successorsBySkillId.TryGetValue(successorSkillId, out detail) &&
                   _skillsById.TryGetValue(detail.HeirSkillId, out skill);
        }

        private static bool TableExists(SqliteConnection connection, string name)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText =
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=$name LIMIT 1";
                command.Parameters.AddWithValue("$name", name);
                return command.ExecuteScalar() != null;
            }
        }
    }
}
