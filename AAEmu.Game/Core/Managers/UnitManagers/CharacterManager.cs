using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

using AAEmu.Commons.IO;
using AAEmu.Commons.Models;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Char.Creation;
using AAEmu.Game.Models.Game.Char.Templates;
using AAEmu.Game.Models.Game.Chat;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Characters;
using AAEmu.Game.Utils;
using AAEmu.Game.Utils.DB;

using MySql.Data.MySqlClient;

using NLog;

namespace AAEmu.Game.Core.Managers.UnitManagers
{
    public class CharacterManager : Singleton<CharacterManager>
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

        private readonly Dictionary<byte, CharacterTemplate> _templates;
        private readonly Dictionary<int, List<Expand>> _expands;
        private readonly Dictionary<uint, AppellationTemplate> _appellations;
        private readonly Dictionary<uint, ActabilityTemplate> _actabilities;
        private readonly Dictionary<int, ExpertLimit> _expertLimits;
        private readonly Dictionary<int, ExpandExpertLimit> _expandExpertLimits;
        private readonly NativeCharacterCreationCatalog _nativeCreation;

        public CharacterManager()
        {
            _templates = new Dictionary<byte, CharacterTemplate>();
            _expands = new Dictionary<int, List<Expand>>();
            _appellations = new Dictionary<uint, AppellationTemplate>();
            _actabilities = new Dictionary<uint, ActabilityTemplate>();
            _expertLimits = new Dictionary<int, ExpertLimit>();
            _expandExpertLimits = new Dictionary<int, ExpandExpertLimit>();
            _nativeCreation = new NativeCharacterCreationCatalog();
        }

        public CharacterTemplate GetTemplate(byte race, byte gender)
        {
            return _templates[(byte)(16 * gender + race)];
        }

        public AppellationTemplate GetAppellationsTemplate(uint id)
        {
            if (_appellations.ContainsKey(id))
                return _appellations[id];
            return null;
        }

        public List<Expand> GetExpands(int step)
        {
            return _expands[step];
        }

        public ActabilityTemplate GetActability(uint id)
        {
            return _actabilities[id];
        }

        public ExpertLimit GetExpertLimit(int step)
        {
            if (_expertLimits.ContainsKey(step))
                return _expertLimits[step];
            return null;
        }

        public ExpandExpertLimit GetExpandExpertLimit(int step)
        {
            if (_expandExpertLimits.ContainsKey(step))
                return _expandExpertLimits[step];
            return null;
        }

        public void CombatTick(TimeSpan delta)
        {
            // Not sure if we should put this here or world
            foreach (var character in WorldManager.Instance.GetAllCharacters())
            {
                // TODO: Make it so you can also become out of combat if you are not on any aggro lists
                if (character.IsInCombat && character.LastCombatActivity.AddSeconds(30) < DateTime.UtcNow)
                {
                    character.BroadcastPacket(new SCCombatClearedPacket(character.ObjId), true);
                    character.IsInCombat = false;
                }

                if (character.IsInPostCast && character.LastCast.AddSeconds(5) < DateTime.UtcNow)
                {
                    character.IsInPostCast = false;
                }
            }
        }

        public void RegenTick(TimeSpan delta)
        {
            foreach (var character in WorldManager.Instance.GetAllCharacters())
            {
                if (character.IsDead || !character.NeedsRegen || character.IsDrowning)
                    continue;

                if (character.IsInCombat)
                    character.Hp += character.PersistentHpRegen;
                else
                    character.Hp += character.HpRegen;

                if (character.IsInPostCast)
                    character.Mp += character.PersistentMpRegen;
                else
                    character.Mp += character.MpRegen;

                character.Hp = Math.Min(character.Hp, character.MaxHp);
                character.Mp = Math.Min(character.Mp, character.MaxMp);
                character.BroadcastPacket(new SCUnitPointsPacket(character.ObjId, character.Hp, character.Mp), true);
            }
        }

        public void BreathTick(TimeSpan delta)
        {
            foreach (var character in WorldManager.Instance.GetAllCharacters())
            {
                if (character.IsDead || !character.IsUnderWater)
                    continue;

                character.DoChangeBreath();
            }
        }

        public void Load()
        {
            Log.Info("Loading character templates...");

            TickManager.Instance.OnTick.Subscribe(BreathTick, TimeSpan.FromMilliseconds(1000));
            TickManager.Instance.OnTick.Subscribe(CombatTick, TimeSpan.FromMilliseconds(1000));
            TickManager.Instance.OnTick.Subscribe(RegenTick, TimeSpan.FromMilliseconds(1000));
            using (var connection = SQLite.CreateConnection())
            {
                var temp = new Dictionary<uint, byte>();
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM characters";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var template = new CharacterTemplate();
                            var id = reader.GetUInt32("id");
                            template.Race = (Race)reader.GetByte("char_race_id");
                            template.Gender = (Gender)reader.GetByte("char_gender_id");
                            template.ModelId = reader.GetUInt32("model_id");
                            template.FactionId = reader.GetUInt32("faction_id");
                            template.ZoneId = reader.GetUInt32("starting_zone_id");
                            template.ReturnDictrictId = reader.GetUInt32("default_return_district_id");
                            template.ResurrectionDictrictId = reader.GetUInt32("default_resurrection_district_id");
                            using (var command2 = connection.CreateCommand())
                            {
                                command2.CommandText = "SELECT * FROM item_body_parts WHERE model_id=@model_id";
                                command2.Prepare();
                                command2.Parameters.AddWithValue("model_id", template.ModelId);
                                using (var reader2 = new SQLiteWrapperReader(command2.ExecuteReader()))
                                {
                                    while (reader2.Read())
                                    {
                                        var itemId = reader2.GetUInt32("item_id", 0);
                                        var slot = reader2.GetInt32("slot_type_id") - 23;
                                        template.Items[slot] = itemId;
                                    }
                                }
                            }

                            var templateId = (byte)(16 * (byte)template.Gender + (byte)template.Race);
                            _templates.Add(templateId, template);
                            temp.Add(id, templateId);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM character_buffs";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var characterId = reader.GetUInt32("character_id");
                            var buffId = reader.GetUInt32("buff_id");
                            var template = _templates[temp[characterId]];
                            template.Buffs.Add(buffId);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM bag_expands";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var expand = new Expand();
                            expand.IsBank = reader.GetBoolean("is_bank", true);
                            expand.Step = reader.GetInt32("step");
                            expand.Price = reader.GetInt32("price");
                            expand.ItemId = reader.GetUInt32("item_id", 0);
                            expand.ItemCount = reader.GetInt32("item_count");
                            expand.CurrencyId = reader.GetInt32("currency_id");

                            if (!_expands.ContainsKey(expand.Step))
                                _expands.Add(expand.Step, new List<Expand> { expand });
                            else
                                _expands[expand.Step].Add(expand);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT id, buff_id FROM appellations";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var template = new AppellationTemplate();
                            template.Id = reader.GetUInt32("id");
                            template.BuffId = reader.GetUInt32("buff_id", 0);

                            _appellations.Add(template.Id, template);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM actability_groups";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var template = new ActabilityTemplate();
                            template.Id = reader.GetUInt32("id");
                            template.Name = reader.GetString("name");
                            template.UnitAttributeId = reader.GetInt32("unit_attr_id");
                            _actabilities.Add(template.Id, template);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM expert_limits ORDER BY up_limit ASC";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        var step = 0;
                        while (reader.Read())
                        {
                            var template = new ExpertLimit();
                            template.Id = reader.GetUInt32("id");
                            template.UpLimit = reader.GetInt32("up_limit");
                            template.ExpertLimitCount = reader.GetByte("expert_limit");
                            template.Advantage = reader.GetInt32("advantage");
                            template.CastAdvantage = reader.GetInt32("cast_adv");
                            template.UpCurrencyId = reader.GetUInt32("up_currency_id", 0);
                            template.UpPrice = reader.GetInt32("up_price");
                            template.DownCurrencyId = reader.GetUInt32("down_currency_id", 0);
                            template.DownPrice = reader.GetInt32("down_price");
                            _expertLimits.Add(step++, template);
                        }
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM expand_expert_limits ORDER BY expand_count ASC";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        var step = 0;
                        while (reader.Read())
                        {
                            var template = new ExpandExpertLimit();
                            //template.Id = reader.GetUInt32("id"); // there is no such field in the database for version 3030
                            template.ExpandCount = reader.GetByte("expand_count");
                            template.LifePoint = reader.GetInt32("life_point");
                            template.ItemId = reader.GetUInt32("item_id", 0);
                            template.ItemCount = reader.GetInt32("item_count");
                            _expandExpertLimits.Add(step++, template);
                        }
                    }
                }
            }

            var filePath = Path.Combine(FileManager.AppPath, "Data", "CharTemplates.json");
            var content = FileManager.GetFileContents(filePath);
            if (string.IsNullOrWhiteSpace(content))
                throw new IOException($"File {filePath} doesn't exists or is empty.");

            if (JsonHelper.TryDeserializeObject(content, out List<CharacterTemplateConfig> charTemplates, out _))
            {
                foreach (var charTemplate in charTemplates)
                {
                    var point = charTemplate.Pos.Clone();
                    // Recalculate ZoneId as this isn't included in the config
                    // Always use main_world Id for this
                    point.ZoneId = WorldManager.Instance.GetZoneId(WorldManager.DefaultWorldId, charTemplate.Pos.X, charTemplate.Pos.Y);

                    // Convert the json's degrees to rads
                    point.Roll = point.Roll.DegToRad();
                    point.Pitch = point.Pitch.DegToRad();
                    point.Yaw = point.Yaw.DegToRad();

                    // Males
                    var template = _templates[(byte)(16 + charTemplate.Id)];
                    template.SpawnPosition = point;
                    template.SpawnPosition.WorldId = WorldManager.DefaultWorldId;
                    template.NumInventorySlot = charTemplate.NumInventorySlot;
                    template.NumBankSlot = charTemplate.NumBankSlot;

                    // Females
                    template = _templates[(byte)(32 + charTemplate.Id)];
                    template.SpawnPosition = point;
                    template.SpawnPosition.WorldId = WorldManager.DefaultWorldId;
                    template.NumInventorySlot = charTemplate.NumInventorySlot;
                    template.NumBankSlot = charTemplate.NumBankSlot;
                }
            }
            else
                throw new Exception($"CharacterManager: Error parsing {filePath} file");

            _nativeCreation.Load(WorldManager.DefaultWorldId);
            if (_nativeCreation.IsReady)
                Log.Info("Loaded immutable AA8 native character-creation catalogue");
            else
                Log.Error(
                    "AA8 native character creation is blocked: {0}",
                    _nativeCreation.FailureReason);

            Log.Info("Loaded {0} character templates", _templates.Count);
        }

        public void PlayerRoll(Character Self, int max)
        {
            byte  cliLocale = 0;
            var roll = Rand.Next(1, max);
            Self.BroadcastPacket(new SCChatMessagePacket(cliLocale, ChatType.System, string.Format(Self.Name + " rolled " + roll.ToString() + ".")), true);

        }

        public void Create(GameConnection connection, string name, byte race, byte gender, uint[] body, UnitCustomModelParams customModel, byte[] ability, byte level, int introZoneId)
        {
            lock (connection.Characters)
            {
                if (!CharacterSlotPolicy.CanCreate(
                        connection.Characters.Count,
                        AppConfiguration.Instance.MaxCharacters))
                {
                    Log.Warn(
                        "Rejected character creation for account {0}: active={1}, maximum={2}",
                        connection.AccountId,
                        connection.Characters.Count,
                        CharacterSlotPolicy.NormalizeMaximum(AppConfiguration.Instance.MaxCharacters));
                    connection.SendPacket(new SCCharacterCreationFailedPacket(3));
                    return;
                }

                CreateUnderAccountLock(connection, name, race, gender, body, customModel, ability, level, introZoneId);
            }
        }

        private void CreateUnderAccountLock(GameConnection connection, string name, byte race, byte gender, uint[] body, UnitCustomModelParams customModel, byte[] ability, byte level, int introZoneId)
        {
            if (!_nativeCreation.TryResolve(
                    race,
                    gender,
                    body,
                    ability,
                    level,
                    introZoneId,
                    out var plan,
                    out var planError))
            {
                Log.Warn(
                    "Rejected AA8 native character creation for account {0}: {1}",
                    connection.AccountId,
                    planError);
                connection.SendPacket(new SCCharacterCreationFailedPacket(3));
                return;
            }

            if (customModel == null ||
                (customModel.ModelId != 0 && customModel.ModelId != plan.ModelId) ||
                (customModel.CharRace != 0 && customModel.CharRace != race) ||
                (customModel.CharGender != 0 && customModel.CharGender != gender))
            {
                Log.Warn(
                    "Rejected AA8 native character model for account {0}: " +
                    "expected={1}/{2}/{3}, received={4}/{5}/{6}",
                    connection.AccountId,
                    plan.ModelId,
                    race,
                    gender,
                    customModel?.ModelId ?? 0,
                    customModel?.CharRace ?? 0,
                    customModel?.CharGender ?? 0);
                connection.SendPacket(new SCCharacterCreationFailedPacket(3));
                return;
            }
            customModel.SetCharacterIdentity(race, gender, plan.ModelId);

            var nameValidationCode = NameManager.Instance.ValidationCharacterName(name);
            if (nameValidationCode != 0)
            {
                connection.SendPacket(new SCCharacterCreationFailedPacket(nameValidationCode));
                return;
            }

            var characterId = CharacterIdManager.Instance.GetNextId();
            if (characterId == 0)
            {
                connection.SendPacket(new SCCharacterCreationFailedPacket(3));
                return;
            }
            if (!NameManager.Instance.TryReserveCharacterName(
                    characterId, name, out nameValidationCode))
            {
                CharacterIdManager.Instance.ReleaseId(characterId);
                connection.SendPacket(new SCCharacterCreationFailedPacket(nameValidationCode));
                return;
            }

            var createdItems = new List<Item>();
            var committed = false;
            try
            {
                var character = MaterializeNativeCharacter(
                    connection, characterId, name, customModel, plan, createdItems);
                if (!character.SaveNewCharacterToDatabase(createdItems))
                    throw new InvalidOperationException(
                        "AA8 native creation transaction did not commit");

                committed = true;
                connection.Characters.Add(character.Id, character);
                connection.SendPacket(new SCCreateCharacterResponsePacket(character));
            }
            catch (Exception exception)
            {
                Log.Error(
                    exception,
                    "AA8 native character creation failed for account {0}, characterId {1}",
                    connection.AccountId,
                    characterId);
                if (!committed)
                    connection.SendPacket(new SCCharacterCreationFailedPacket(3));
            }
            finally
            {
                if (!committed)
                {
                    ItemManager.Instance.RollbackCreatedItems(createdItems);
                    NameManager.Instance.RemoveCharacterName(characterId);
                    CharacterIdManager.Instance.ReleaseId(characterId);
                }
            }
        }

        private Character MaterializeNativeCharacter(
            GameConnection connection,
            uint characterId,
            string name,
            UnitCustomModelParams customModel,
            CharacterBootstrapPlan plan,
            ICollection<Item> createdItems)
        {
            var faction = FactionManager.Instance.GetFaction(plan.FactionId);
            if (faction == null)
                throw new InvalidOperationException(
                    $"AA8 character template references missing faction {plan.FactionId}");

            var character = new Character(customModel)
            {
                Id = characterId,
                AccountId = connection.AccountId,
                Name = name.Substring(0, 1).ToUpperInvariant() + name.Substring(1),
                Race = plan.Race,
                Gender = plan.Gender,
                ModelId = plan.ModelId,
                Level = NativeCharacterCreationCatalog.NativeLevel,
                Faction = faction,
                FactionName = string.Empty,
                AccessLevel = 100,
                LaborPower = 50,
                LaborPowerModified = DateTime.UtcNow,
                NumInventorySlots = plan.InventorySlots,
                NumBankSlots = plan.BankSlots,
                Created = DateTime.UtcNow,
                Updated = DateTime.UtcNow,
                Ability1 = plan.InitialAbility,
                Ability2 = AbilityType.None,
                Ability3 = AbilityType.None,
                ReturnDictrictId = plan.ReturnDistrictId,
                ResurrectionDictrictId = plan.ResurrectionDistrictId,
                Slots = plan.Actions
                    .Select(x => new ActionSlot { Type = x.Type, ActionId = x.ActionId })
                    .ToArray()
            };
            character.Transform.ApplyWorldSpawnPosition(plan.Spawn);
            character.Inventory = new Inventory(character);

            foreach (var itemPlan in plan.Equipment.Concat(plan.Supplies))
            {
                var container = itemPlan.Container == SlotType.Equipment
                    ? character.Inventory.Equipment
                    : character.Inventory.Bag;
                var item = ItemManager.Instance.Create(
                    itemPlan.TemplateId,
                    itemPlan.Amount,
                    itemPlan.Grade);
                if (item == null)
                    throw new InvalidOperationException(
                        $"failed to create AA8 item {itemPlan.TemplateId}");
                createdItems.Add(item);
                if (!container.AddOrMoveExistingItem(
                        ItemTaskType.Invalid,
                        item,
                        itemPlan.Slot) ||
                    item.SlotType != itemPlan.Container ||
                    item.Slot != itemPlan.Slot)
                {
                    throw new InvalidOperationException(
                        $"failed to materialize AA8 item {itemPlan.TemplateId} in " +
                        $"{itemPlan.Container}/{itemPlan.Slot}");
                }
            }

            character.Abilities = new CharacterAbilities(character);
            character.Abilities.SetAbility(character.Ability1, 0);

            character.Actability = new CharacterActability(character);
            foreach (var (id, actabilityTemplate) in _actabilities)
                character.Actability.Actabilities.Add(id, new Actability(actabilityTemplate));

            character.Skills = new CharacterSkills(character);
            foreach (var skillId in plan.LearnedSkills.Distinct())
            {
                var template = SkillManager.Instance.GetSkillTemplate(skillId);
                if (!character.Skills.AddSkill(template, 1, false))
                    throw new InvalidOperationException(
                        $"failed to add native AA8 initial skill {skillId}");
            }

            character.SkillActiveTypes = new CharacterSkillActiveTypes(character);
            character.HeirSkills = new CharacterHeirSkills(character);

            character.Appellations = new CharacterAppellations(character);
            character.Quests = new CharacterQuests(character);
            character.Mails = new CharacterMails(character);
            character.Portals = new CharacterPortals(character);
            character.Friends = new CharacterFriends(character);
            character.Hp = character.MaxHp;
            character.Mp = character.MaxMp;
            return character;
        }

        /// <summary>
        /// Removed all items and assets this character currently owns
        /// </summary>
        /// <param name="character">Character to delete assets from</param>
        /// <param name="fullWipe">Do owned items need to be actually deleted</param>
        public void DeleteCharacterAssets(Character character, bool fullWipe)
        {
            // Demolish owned houses
            var myHouses = new Dictionary<uint, House>();
            if (HousingManager.Instance.GetByCharacterId(myHouses, character.Id) > 0)
            {
                foreach (var (houseId, house) in myHouses)
                {
                    house.Permission = HousingPermission.Public;
                    // force expire the house
                    // This should technically kill the house, and return the minimum amount of furniture
                    house.ProtectionEndDate = DateTime.UtcNow.AddDays(-21);
                    HousingManager.Instance.UpdateTaxInfo(house);
                }
            }

            // Remove from Guild
            if (character.Expedition != null)
                ExpeditionManager.Instance.Leave(character);

            // Remove from Family
            if (character.Family > 0)
                FamilyManager.Instance.LeaveFamily(character);

            // TODO: Remove from player nation
            // TODO: Delete leadership

            // Return all mails to sender (if needed)
            // The main reason we do this is so other people's items wouldn't get delete if fullWipe is enabled
            foreach (var (mailId, mail) in MailManager.Instance._allPlayerMails)
            {
                if (mail.CanReturnMail() && !mail.ReturnToSender())
                    Log.Warn(
                        "DeleteCharacterAssets - Unable to return mail to sender for mail: {0}, deleted char: {1}({2}), sender: {3}({4})",
                        mail.Id,
                        mail.Header.ReceiverName, mail.Header.ReceiverId,
                        mail.Header.SenderName, mail.Header.SenderId);
            }

            if (!fullWipe)
                return;

            Log.Warn("DeleteCharacterAssets - fullWipe is currently not implemented yet, charId: {0}", character.Id);
            // TODO: Wipe all mails
            // TODO: Wipe all items/gold (this also deletes all pets/vehicles)
        }

        /// <summary>
        /// Mark characters marked for deletion as deleted after their time is finished
        /// </summary>
        /// <param name="character"></param>
        /// <param name="gameConnection"></param>
        /// <param name="dbConnection"></param>
        /// <returns>Returns true if a character was marked deleted, otherwise false</returns>
        public bool CheckForDeletedCharactersDeletion(Character character, GameConnection gameConnection, MySqlConnection dbConnection)
        {
            if (character.DeleteTime > DateTime.MinValue && character.DeleteTime <= DateTime.UtcNow)
            {
                Log.Info("CheckForDeletedCharactersDeletion - Deleting Account:{0} Id:{1} Name:{2}", character.AccountId, character.Id, character.Name);
                using (var command = dbConnection.CreateCommand())
                {
                    var deletedName = character.Name;
                    if (AppConfiguration.Instance.Account.DeleteReleaseName)
                    {
                        deletedName = "!" + character.Name;
                        NameManager.Instance.RemoveCharacterName(character.Id);
                        NameManager.Instance.AddCharacterName(character.Id, deletedName);
                    }

                    command.Connection = dbConnection;
                    command.CommandText = "UPDATE `characters` SET `deleted`='1', `delete_time`=@new_delete_time, `name`=@deletedname WHERE `id`=@char_id and `account_id`=@account_id;";
                    command.Parameters.AddWithValue("@new_delete_time", DateTime.MinValue);
                    command.Parameters.AddWithValue("@char_id", character.Id);
                    command.Parameters.AddWithValue("@account_id", character.AccountId);
                    command.Parameters.AddWithValue("@deletedname", deletedName);

                    var res = command.ExecuteNonQuery();
                    // Send update to current connection
                    if (res > 0)
                    {
                        DeleteCharacterAssets(character, false);

                        // Send delete packet to the player if online
                        if (gameConnection != null)
                        {
                            gameConnection.SendPacket(new SCCharacterDeletedPacket(character.Id, character.Name));
                            // Not sure if this is the way it should be send or not, but it seems to work with status 1
                            gameConnection.SendPacket(new SCCharacterDeleteResponsePacket(character.Id, 1, character.DeleteRequestTime, character.DeleteTime));
                        }
                    }
                    return res > 0;
                }
            }
            else
            if (character.DeleteRequestTime > DateTime.MinValue)
            {
                Log.Warn("CheckForDeletedCharactersDeletion - Delete request for Account:{0} Id:{1} Name:{2}, but character is no longer marked for deletion (possibly cancelled delete)", character.AccountId, character.Id, character.Name);
            }
            return false;
        }

        public void CheckForDeletedCharacters()
        {
            var nextCheckTime = DateTime.MaxValue;
            var deleteList = new List<(uint, ulong)>(); // charId, accountId

            Log.Debug("CheckForDeletedCharacters - Begin");
            using (var connection = MySQL.CreateConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    // TODO: Update this query to be more efficient
                    command.CommandText = "SELECT `id`, `name`, `account_id`, `delete_time` FROM characters WHERE `deleted`=0";
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            // Check the delete time for this entry
                            var deleteTime = reader.GetDateTime("delete_time");
                            var charId = reader.GetUInt32("id");
                            var accountId = reader.GetUInt64("account_id");
                            if (deleteTime > DateTime.MinValue && deleteTime <= DateTime.UtcNow)
                            {
                                deleteList.Add((charId, accountId));
                            }
                            else
                            if (deleteTime > DateTime.MinValue && deleteTime < nextCheckTime)
                            {
                                nextCheckTime = deleteTime;
                            }
                        }
                    }
                }

                // Actually start deleting
                foreach (var (charId, accountId) in deleteList)
                {
                    var character = Character.Load(connection, charId, accountId);
                    if (character != null)
                    {
                        var accountConnection = GameConnectionTable.Instance?.GetConnectionByAccount(character.AccountId) ?? null;
                        if (CheckForDeletedCharactersDeletion(character, accountConnection, connection))
                            Log.Info("CheckForDeletedCharacters - Delete charId:{0}", charId);
                        else
                            // Failed to delete character from DB
                            Log.Error("CheckForDeletedCharacters - Failed to delete character for deletion charId:{0}", charId);
                    }
                    else
                    {
                        // Failed to load character for deletion somehow
                        Log.Error("CheckForDeletedCharacters - Failed to load character for deletion charId:{0}", charId);
                    }
                }
            }

            // Start a Delete Tick Task
            if (nextCheckTime < DateTime.MaxValue)
            {
                var deleteCheckTask = new CharacterDeleteTask();
                TaskManager.Instance?.Schedule(deleteCheckTask, nextCheckTime - DateTime.UtcNow);
                Log.Debug("CheckForDeletedCharacters - Next delete scheduled at " + nextCheckTime.ToString());
            }
            else
            {
                Log.Debug("CheckForDeletedCharacters - No new deletions scheduled");
            }
        }

        public void SetDeleteCharacter(GameConnection gameConnection, uint characterId)
        {
            if (gameConnection.Characters.ContainsKey(characterId))
            {
                var character = gameConnection.Characters[characterId];
                character.DeleteRequestTime = DateTime.UtcNow;

                var targetDeleteDelay = 0;

                // Get timings from settings
                foreach (var timing in AppConfiguration.Instance.Account.DeleteTimings)
                {
                    if (character.Level >= timing.Level)
                        targetDeleteDelay = timing.Delay;
                }

                // Add the actual timing
                character.DeleteTime = character.DeleteRequestTime.AddMinutes(targetDeleteDelay);

                using (var connection = MySQL.CreateConnection())
                {
                    using (var command = connection.CreateCommand())
                    {
                        command.CommandText =
                            "UPDATE characters SET `delete_request_time` = @delete_request_time, `delete_time` = @delete_time WHERE `id` = @id";
                        command.Prepare();
                        command.Parameters.AddWithValue("@delete_request_time", character.DeleteRequestTime);
                        command.Parameters.AddWithValue("@delete_time", character.DeleteTime);
                        command.Parameters.AddWithValue("@id", character.Id);
                        if (command.ExecuteNonQuery() == 1)
                        {
                            gameConnection.SendPacket(new SCCharacterDeleteResponsePacket(character.Id, 2, character.DeleteRequestTime, character.DeleteTime));
                        }
                        else
                        {
                            // Failed to mark for deletion
                            // Not the correct message, but it seems funny enough
                            gameConnection.SendPacket(new SCErrorMsgPacket(ErrorMessageType.CannotDeleteCharWhileBotSuspected, 0, true));
                        }

                    }
                }
            }
            else
            {
                gameConnection.SendPacket(new SCCharacterDeleteResponsePacket(characterId, 0));
            }
            // Trigger our task queueing
            CheckForDeletedCharacters();
        }

        public void SetRestoreCharacter(GameConnection gameConnection, uint characterId)
        {
            if (gameConnection.Characters.ContainsKey(characterId))
            {
                var character = gameConnection.Characters[characterId];
                character.DeleteRequestTime = DateTime.MinValue;
                character.DeleteTime = DateTime.MinValue;
                gameConnection.SendPacket(new SCCancelCharacterDeleteResponsePacket(character.Id, 3));

                using (var connection = MySQL.CreateConnection())
                {
                    using (var command = connection.CreateCommand())
                    {
                        command.CommandText =
                            "UPDATE characters SET `delete_request_time` = @delete_request_time, `delete_time` = @delete_time WHERE `id` = @id";
                        command.Prepare();
                        command.Parameters.AddWithValue("@delete_request_time", character.DeleteRequestTime);
                        command.Parameters.AddWithValue("@delete_time", character.DeleteTime);
                        command.Parameters.AddWithValue("@id", character.Id);
                        command.ExecuteNonQuery();
                    }
                }
            }
            else
            {
                gameConnection.SendPacket(new SCCancelCharacterDeleteResponsePacket(characterId, 4));
            }
        }
        public List<LoginCharacterInfo> LoadCharacters(ulong accountId)
        {
            var result = new List<LoginCharacterInfo>();
            using (var connection = MySQL.CreateConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT `id`, `name`, `race`, `gender`,`delete_time` FROM characters WHERE `account_id`=@accountId and `deleted`=0";
                    command.Parameters.AddWithValue("@accountId", accountId);
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            // Skip this char in the list if it's read to be deleted
                            var deleteTime = reader.GetDateTime("delete_time");
                            if (deleteTime > DateTime.MinValue && deleteTime < DateTime.UtcNow)
                                continue;

                            var character = new LoginCharacterInfo();
                            character.AccountId = accountId;
                            character.Id = reader.GetUInt32("id");
                            character.Name = reader.GetString("name");
                            character.Race = reader.GetByte("race");
                            character.Gender = reader.GetByte("gender");
                            result.Add(character);
                        }
                    }
                }
            }
            return result;
        }

        public void ApplyBeautySalon(Character character, uint hairModel, UnitCustomModelParams modelParams)
        {
            // TODO: Add support for future X-day Salon Certificate items

            if (character.Inventory.GetItemsCount(SlotType.Inventory, Item.SalonCertificate) <= 0)
                return;

            var oldHair = character.Equipment.GetItemBySlot((byte)EquipmentItemSlot.Hair);

            // Check if hair changed
            if (oldHair != null && oldHair.TemplateId != hairModel)
            {
                // Remove old hair item
                oldHair._holdingContainer.RemoveItem(ItemTaskType.Invalid, oldHair, true);
                // Create new hair item
                if (!character.Equipment.AcquireDefaultItemEx(ItemTaskType.Invalid, hairModel, 1, -1,
                        out var newItemsList, out var _, character.Id, (int)EquipmentItemSlot.Hair))
                {
                    Log.Error($"Failed to add new hairstyle for player {character.Name} ({character.Id})!");
                }

                if (newItemsList.Count != 1)
                {
                    Log.Error($"Something failed during hairstyle creation for player {character.Name} ({character.Id})!");
                }

            }
            character.ModelParams = modelParams;

            character.BroadcastPacket(new SCCharacterGenderAndModelModifiedPacket(character), true);

            if (character.Inventory.Bag.ConsumeItem(ItemTaskType.EditCosmetic, Item.SalonCertificate, 1, null) <= 0)
                Log.Error($"Could not consume salon certificate for player {character.Name} ({character.Id})!");

            // The client will do a salon leave request after it gets the SCCharacterGenderAndModelModifiedPacket
        }
    }
}
