using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;

using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Models.Game.Char
{
    public class CharacterAbilities
    {
        private const byte InitialInactiveAbilityLevel = 15;
        private static readonly Logger _log = LogManager.GetCurrentClassLogger();

        public Dictionary<AbilityType, Ability> Abilities { get; set; }
        public Character Owner { get; set; }

        public CharacterAbilities(Character owner)
        {
            Owner = owner;
            Abilities = new Dictionary<AbilityType, Ability>();
            for (var i = 1; i < 30; i++) //read_Exp_Order 1.2 = 10 ability, 3.0.3.0 = 12 ability , 5.7.5.0 = 29 ability, 7.0.3.9 = 29
            {
                var id = (AbilityType)i;
                Abilities[id] = new Ability(id);
            }
        }

        public IEnumerable<Ability> Values => Abilities.Values;

        public void SetAbility(AbilityType id, byte order)
        {
            if (id != AbilityType.None && Abilities.TryGetValue(id, out var ability))
                ability.Order = order;
        }

        public List<AbilityType> GetActiveAbilities()
        {
            var list = new List<AbilityType>();
            if (Owner.Ability1 != AbilityType.None)
                list.Add(Owner.Ability1);
            if (Owner.Ability2 != AbilityType.None)
                list.Add(Owner.Ability2);
            if (Owner.Ability3 != AbilityType.None)
                list.Add(Owner.Ability3);
            return list;
        }

        public void AddExp(AbilityType type, int exp)
        {
            // TODO SCAbilityExpChangedPacket
            if (type != AbilityType.None)
                Abilities[type].Exp += exp;
        }

        public void AddActiveExp(int exp)
        {
            // TODO SCExpChangedPacket
            if (Owner.Ability1 != AbilityType.None)
                Abilities[Owner.Ability1].Exp = Math.Min(Abilities[Owner.Ability1].Exp + exp, ExpirienceManager.Instance.GetExpForLevel(55));
            if (Owner.Ability2 != AbilityType.None)
                Abilities[Owner.Ability2].Exp = Math.Min(Abilities[Owner.Ability2].Exp + exp, ExpirienceManager.Instance.GetExpForLevel(55));
            if (Owner.Ability3 != AbilityType.None)
                Abilities[Owner.Ability3].Exp = Math.Min(Abilities[Owner.Ability3].Exp + exp, ExpirienceManager.Instance.GetExpForLevel(55));
        }

        public bool Swap(AbilityType oldAbilityId, AbilityType abilityId)
        {
            var activeAbilities = GetActiveAbilities();
            if (!Abilities.ContainsKey(abilityId) || abilityId == AbilityType.None || activeAbilities.Contains(abilityId))
                return false;

            var isFirstActivation = Abilities[abilityId].Exp <= 0;

            var slot = oldAbilityId == AbilityType.None
                ? GetFirstEmptySlot()
                : GetAbilitySlot(oldAbilityId);
            if (slot < 0)
                return false;

            if (isFirstActivation)
            {
                var initialLevelExp = ExpirienceManager.Instance.GetExpForLevel(InitialInactiveAbilityLevel);
                Abilities[abilityId].Exp = CalculateInitialAbilityExp(Owner.Expirience, initialLevelExp);
                _log.Info(
                    "Initialized first ability activation: character={0}, ability={1}, exp={2}, level={3}",
                    Owner.Name, abilityId, Abilities[abilityId].Exp, InitialInactiveAbilityLevel);
            }

            if (oldAbilityId != AbilityType.None)
            {
                Owner.Skills.Reset(oldAbilityId);
                Abilities[oldAbilityId].Order = 255;
            }

            SetAbilitySlot(slot, abilityId);
            RebuildOrders();

            Owner.BroadcastPacket(
                new SCAbilitySwappedPacket(Owner.ObjId, oldAbilityId, abilityId), true);

            // AA8 only allocates client-side ability EXP when the entry is new, but always raises
            // ABILITY_SET_CHANGED. Emit this after the slot snapshot so the refresh sees new slots.
            Owner.SendPacket(new SCSpecialAbilityActivedPacket(abilityId));

            Owner.Skills.AddAutomaticSkills(abilityId);
            return true;
        }

        private static int CalculateInitialAbilityExp(int characterExp, int initialLevelExp)
        {
            return Math.Min(Math.Max(characterExp, 0), Math.Max(initialLevelExp, 0));
        }

        private int GetAbilitySlot(AbilityType abilityId)
        {
            if (Owner.Ability1 == abilityId)
                return 0;
            if (Owner.Ability2 == abilityId)
                return 1;
            if (Owner.Ability3 == abilityId)
                return 2;
            return -1;
        }

        private int GetFirstEmptySlot()
        {
            return GetAbilitySlot(AbilityType.None);
        }

        private void SetAbilitySlot(int slot, AbilityType abilityId)
        {
            if (slot == 0)
                Owner.Ability1 = abilityId;
            else if (slot == 1)
                Owner.Ability2 = abilityId;
            else if (slot == 2)
                Owner.Ability3 = abilityId;
        }

        private void RebuildOrders()
        {
            foreach (var ability in Abilities.Values)
                ability.Order = 255;
            SetAbility(Owner.Ability1, 0);
            SetAbility(Owner.Ability2, 1);
            SetAbility(Owner.Ability3, 2);
        }

        public void Load(MySqlConnection connection)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM abilities WHERE `owner` = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var ability = new Ability
                        {
                            Id = (AbilityType)reader.GetByte("id"),
                            Exp = reader.GetInt32("exp")
                        };
                        if (ability.Id == Owner.Ability1)
                            ability.Order = 0;
                        if (ability.Id == Owner.Ability2)
                            ability.Order = 1;
                        if (ability.Id == Owner.Ability3)
                            ability.Order = 2;
                        Abilities[ability.Id] = ability;
                    }
                }
            }
        }

        public void Save(MySqlConnection connection, MySqlTransaction transaction)
        {
            foreach (var ability in Abilities.Values)
            {
                using (var command = connection.CreateCommand())
                {
                    command.Connection = connection;
                    command.Transaction = transaction;

                    command.CommandText = "REPLACE INTO abilities(`id`,`exp`,`owner`) VALUES (@id, @exp, @owner)";
                    command.Parameters.AddWithValue("@id", (byte)ability.Id);
                    command.Parameters.AddWithValue("@exp", ability.Exp);
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();
                }
            }
        }
    }
}
