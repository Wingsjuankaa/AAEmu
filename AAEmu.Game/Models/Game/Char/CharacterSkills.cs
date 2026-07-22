using System;
using System.Collections.Generic;
using System.Linq;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Models.Game.Char
{
    public class CharacterSkills
    {
        private static readonly Logger _log = LogManager.GetCurrentClassLogger();

        private enum SkillType : byte
        {
            Skill = 1,
            Buff = 2
        }

        public Dictionary<uint, Skill> Skills { get; set; }
        public Dictionary<uint, PassiveBuff> PassiveBuffs { get; set; }

        public Character Owner { get; set; }

        public CharacterSkills(Character owner)
        {
            Owner = owner;
            Skills = new Dictionary<uint, Skill>();
            PassiveBuffs = new Dictionary<uint, PassiveBuff>();
        }

        public bool AddSkill(uint skillId)
        {
            var template = SkillManager.Instance.GetSkillTemplate(skillId);
            if (template == null)
            {
                _log.Warn("Rejected unknown skill: character={0}, skill={1}", Owner.Name, skillId);
                return false;
            }

            if (!IsAbilityActive(template.AbilityId))
            {
                _log.Warn(
                    "Rejected skill from inactive ability: character={0}, skill={1}, ability={2}",
                    Owner.Name, skillId, template.AbilityId);
                return false;
            }

            if (Skills.TryGetValue(skillId, out var existingSkill))
            {
                Owner.SendPacket(new SCSkillLearnedPacket(existingSkill));
                return true;
            }

            var availablePoints = ExpirienceManager.Instance.GetSkillPointsForLevel(Owner.Level) - GetUsedSkillPoints();
            if (template.SkillPoints > availablePoints)
            {
                _log.Warn(
                    "Rejected skill without available points: character={0}, skill={1}, cost={2}, available={3}",
                    Owner.Name, skillId, template.SkillPoints, availablePoints);
                return false;
            }

            var spentInAbility = GetUsedSkillPoints(template.AbilityId);
            if (template.ReqPoints > spentInAbility)
            {
                _log.Warn(
                    "Rejected skill without required ability points: character={0}, skill={1}, required={2}, spent={3}",
                    Owner.Name, skillId, template.ReqPoints, spentInAbility);
                return false;
            }

            var abilityLevel = Owner.GetAbLevel((AbilityType)template.AbilityId);
            if (!TryCalculateSkillLevel(abilityLevel, template.AbilityLevel, template.LevelStep, out var skillLevel))
            {
                _log.Warn(
                    "Rejected skill level: character={0}, skill={1}, ability={2}, abilityLevel={3}, requiredLevel={4}, levelStep={5}",
                    Owner.Name, skillId, template.AbilityId, abilityLevel, template.AbilityLevel, template.LevelStep);
                return false;
            }

            return AddSkill(template, skillLevel, true);
        }

        public bool AddSkill(SkillTemplate template, byte level, bool packet)
        {
            if (template == null || level < 1 || Skills.ContainsKey(template.Id))
                return false;

            var skill = new Skill
            {
                Id = template.Id,
                Template = template,
                Level = level
            };
            Skills.Add(skill.Id, skill);

            if (packet)
                Owner.SendPacket(new SCSkillLearnedPacket(skill));
            return true;
        }

        public void AddAutomaticSkills(AbilityType abilityId)
        {
            foreach (var template in SkillManager.Instance.GetStartAbilitySkills(abilityId))
            {
                var abilityLevel = Owner.GetAbLevel(abilityId);
                if (TryCalculateSkillLevel(abilityLevel, template.AbilityLevel, template.LevelStep, out var skillLevel))
                    AddSkill(template, skillLevel, true);
            }
        }

        public bool AddBuff(uint buffId)
        {
            var template = SkillManager.Instance.GetPassiveBuffTemplate(buffId);
            if (template == null)
            {
                _log.Warn("Rejected unknown passive: character={0}, passive={1}", Owner.Name, buffId);
                return false;
            }

            if (!IsAbilityActive(template.AbilityId) || PassiveBuffs.ContainsKey(buffId))
                return false;

            var abilityLevel = Owner.GetAbLevel((AbilityType)template.AbilityId);
            if (abilityLevel < template.Level)
                return false;

            var availablePoints = ExpirienceManager.Instance.GetSkillPointsForLevel(Owner.Level) - GetUsedSkillPoints();
            if (template.SkillPoints > availablePoints || template.ReqPoints > GetUsedSkillPoints(template.AbilityId))
                return false;

            if (SkillManager.Instance.GetBuffTemplate(template.BuffId) == null)
            {
                _log.Warn(
                    "Rejected passive with missing buff template: character={0}, passive={1}, buff={2}",
                    Owner.Name, buffId, template.BuffId);
                return false;
            }

            var buff = new PassiveBuff { Id = buffId, Template = template };
            PassiveBuffs.Add(buff.Id, buff);
            Owner.BroadcastPacket(new SCBuffLearnedPacket(Owner.ObjId, buff.Id), true);
            buff.Apply(Owner);
            return true;
        }

        public bool Reset(AbilityType abilityId)
        {
            if (!Owner.Abilities.GetActiveAbilities().Contains(abilityId))
                return false;

            foreach (var skill in Skills.Values.Where(x => x.Template.AbilityId == (byte)abilityId).ToList())
                Skills.Remove(skill.Id);

            foreach (var buff in PassiveBuffs.Values.Where(x => x.Template.AbilityId == (byte)abilityId).ToList())
            {
                buff.Remove(Owner);
                PassiveBuffs.Remove(buff.Id);
            }

            Owner.BroadcastPacket(new SCSkillsResetPacket(Owner.ObjId, abilityId), true);
            return true;
        }

        public int GetUsedSkillPoints(byte? abilityId = null)
        {
            var skillPoints = Skills.Values
                .Where(x => abilityId == null || x.Template.AbilityId == abilityId)
                .Sum(x => x.Template.SkillPoints);
            var passivePoints = PassiveBuffs.Values
                .Where(x => abilityId == null || x.Template.AbilityId == abilityId)
                .Sum(x => x.Template?.SkillPoints ?? 0);
            return skillPoints + passivePoints;
        }

        public static bool TryCalculateSkillLevel(int abilityLevel, int requiredLevel, int levelStep, out byte skillLevel)
        {
            skillLevel = 0;
            if (abilityLevel < requiredLevel)
                return false;

            var calculatedLevel = levelStep > 0
                ? (abilityLevel - requiredLevel) / levelStep + 1
                : 1;
            if (calculatedLevel < 1 || calculatedLevel > sbyte.MaxValue)
                return false;

            skillLevel = (byte)calculatedLevel;
            return true;
        }

        // TODO : Optimize this by storing a map of derivative skills and their matches
        public bool IsVariantOfSkill(uint skillId)
        {
            var skillTemplate = SkillManager.Instance.GetSkillTemplate(skillId);
            if (skillTemplate == null)
                return false;

            return Skills.Values.Any(skill =>
                skill.Template.AbilityId == skillTemplate.AbilityId &&
                skill.Template.AbilityLevel == skillTemplate.AbilityLevel);
        }

        private bool IsAbilityActive(byte abilityId)
        {
            return abilityId == 0 || Owner.Abilities.GetActiveAbilities().Contains((AbilityType)abilityId);
        }

        private bool IsPersistedSkillLevelValid(SkillTemplate template, byte level)
        {
            if (level < 1)
                return false;
            if (template.AbilityId == 0)
                return level <= sbyte.MaxValue;

            var abilityLevel = Owner.GetAbLevel((AbilityType)template.AbilityId);
            return TryCalculateSkillLevel(
                abilityLevel, template.AbilityLevel, template.LevelStep, out var maximumLevel) &&
                level <= maximumLevel;
        }

        #region database
        public void Load(MySqlConnection connection)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM skills WHERE `owner` = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var id = reader.GetUInt32("id");
                        if (!Enum.TryParse(reader.GetString("type"), true, out SkillType type))
                        {
                            _log.Warn("Skipped persisted entry with invalid type: character={0}, id={1}", Owner.Name, id);
                            continue;
                        }

                        if (type == SkillType.Skill)
                        {
                            var template = SkillManager.Instance.GetSkillTemplate(id);
                            var level = reader.GetByte("level");
                            if (template == null || !IsAbilityActive(template.AbilityId) ||
                                !IsPersistedSkillLevelValid(template, level))
                            {
                                _log.Warn(
                                    "Skipped invalid persisted skill: character={0}, skill={1}, level={2}",
                                    Owner.Name, id, level);
                                continue;
                            }

                            AddSkill(template, level, false);
                            continue;
                        }

                        var passiveTemplate = SkillManager.Instance.GetPassiveBuffTemplate(id);
                        if (passiveTemplate == null || !IsAbilityActive(passiveTemplate.AbilityId) ||
                            SkillManager.Instance.GetBuffTemplate(passiveTemplate.BuffId) == null)
                        {
                            _log.Warn("Skipped invalid persisted passive: character={0}, passive={1}", Owner.Name, id);
                            continue;
                        }

                        var buff = new PassiveBuff { Id = id, Template = passiveTemplate };
                        PassiveBuffs.Add(buff.Id, buff);
                        buff.Apply(Owner);
                    }
                }
            }
        }

        public void Save(MySqlConnection connection, MySqlTransaction transaction)
        {
            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;
                command.CommandText = "DELETE FROM skills WHERE owner = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                command.ExecuteNonQuery();
            }

            foreach (var skill in Skills.Values)
            {
                using (var command = connection.CreateCommand())
                {
                    command.Connection = connection;
                    command.Transaction = transaction;
                    command.CommandText =
                        "INSERT INTO skills(`id`,`level`,`type`,`owner`) VALUES (@id, @level, @type, @owner)";
                    command.Parameters.AddWithValue("@id", skill.Id);
                    command.Parameters.AddWithValue("@level", skill.Level);
                    command.Parameters.AddWithValue("@type", (byte)SkillType.Skill);
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();
                }
            }

            foreach (var buff in PassiveBuffs.Values)
            {
                using (var command = connection.CreateCommand())
                {
                    command.Connection = connection;
                    command.Transaction = transaction;
                    command.CommandText =
                        "INSERT INTO skills(`id`,`level`,`type`,`owner`) VALUES(@id,@level,@type,@owner)";
                    command.Parameters.AddWithValue("@id", buff.Id);
                    command.Parameters.AddWithValue("@level", 1);
                    command.Parameters.AddWithValue("@type", (byte)SkillType.Buff);
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();
                }
            }
        }

        #endregion
    }
}
