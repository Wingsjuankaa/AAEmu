using System.Data;
using System.Data.Common;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Mate;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.Game.Models.Game.Char;

public enum MateToggleResult
{
    Rejected,
    Spawned,
    Despawned
}

public class CharacterMates(Character owner)
{
    /*
     * TODO:
     * EQUIPMENT CHANGE
     * FINISH ATTRIBUTES
     * NAME FROM LOCALIZED TABLE
     */

    private Character Owner { get; set; } = owner;

    private object _mateLifecycleLock => _saveSync;
    private readonly HashSet<uint> _removedMates = [];
    private readonly Dictionary<ulong, MateDb> _mates = []; // itemId, MountDb
    private readonly object _saveSync = new();

    public MateDb GetMateInfo(ulong itemId)
    {
        lock (_saveSync)
            return _mates.GetValueOrDefault(itemId)?.Clone();
    }

    /// <summary>
    /// Applies a state update under the save lock and returns a detached snapshot. The update is an
    /// in-memory write only; the row reaches the database with the next <see cref="Save"/>, so this
    /// never blocks a gameplay thread on an unrelated character's save transaction.
    /// </summary>
    public MateDb UpdateMateInfo(ulong itemId, Action<MateDb> update)
    {
        ArgumentNullException.ThrowIfNull(update);
        lock (_saveSync)
        {
            if (!_mates.TryGetValue(itemId, out var current))
                return null;

            var updated = current.Clone();
            update(updated);
            updated.Id = current.Id;
            updated.ItemId = current.ItemId;
            updated.Owner = current.Owner;
            _mates[itemId] = updated;
            return updated.Clone();
        }
    }

    private MateDb CreateNewMate(ulong itemId, NpcTemplate npcTemplate)
    {
        lock (_saveSync)
        {
            if (_mates.ContainsKey(itemId)) return null;
        }
        var template = new MateDb
        {
            // TODO
            Id = MateIdManager.Instance.GetNextId(),
            ItemId = itemId,
            Level = npcTemplate.Level,
            Name = LocalizationManager.Instance.Get("npcs", "name", npcTemplate.Id, npcTemplate.Name), // npcTemplate.Name,
            Owner = Owner.Id,
            Mileage = 0,
            Xp = ExperienceManager.Instance.GetExpForLevel(npcTemplate.Level, true),
            // Zero on both bars is "this mate has never been summoned, so it has no recorded recovery".
            // It is not a health or mana value: the summon path reads it through MateRecoveryRules,
            // which starts a mate with no recorded bar at the maximum its content reconstructs. It is
            // a state of its own rather than 0, because 0 is a bar that really was empty.
            Hp = MateRecoveryRules.Unrecorded,
            Mp = MateRecoveryRules.Unrecorded,
            UpdatedAt = DateTime.UtcNow,
            CreatedAt = DateTime.UtcNow
        };
        lock (_saveSync)
        {
            if (!_mates.TryAdd(template.ItemId, template))
                return null;
        }
        return template.Clone();
    }

    public (SummonMateTemplate ItemTemplate, NpcTemplate NpcTemplate, MateRecoveryState RecoveryState)
        ResolveSummonMate(uint itemTemplateId)
    {
        if (ItemManager.Instance.GetTemplate(itemTemplateId) is not SummonMateTemplate itemTemplate)
        {
            throw new InvalidDataException(
                $"Summon mate item {itemTemplateId} has no item_summon_mates template.");
        }

        var npcId = itemTemplate.NpcId;
        var npcTemplate = NpcManager.Instance.GetTemplate(npcId)
            ?? throw new InvalidDataException(
                $"Summon mate item {itemTemplateId} references missing NPC template {npcId}.");
        var recoveryState = MateGameData.Instance.GetRecoveryState(itemTemplate);
        return (itemTemplate, npcTemplate, recoveryState);
    }

    public MateToggleResult ToggleMate(SkillItem skillData, SummonMateContract contract)
    {
        lock (_mateLifecycleLock)
            return ToggleMateLocked(skillData, contract);
    }

    private MateToggleResult ToggleMateLocked(SkillItem skillData, SummonMateContract contract)
    {
        if (skillData is null || contract is null)
            return MateToggleResult.Rejected;

        // Revalidate the complete relationship before despawning a mate or allocating IDs.
        var item = Owner.Inventory.GetItemById(skillData.ItemId);
        if (item is not SummonMate summonMate || item.Template is not SummonMateTemplate itemTemplate ||
            item.Id != skillData.ItemId || item.OwnerId != Owner.Id ||
            item.SlotType != SlotType.Inventory ||
            item._holdingContainer is not { ContainerType: SlotType.Inventory } container ||
            container.OwnerId != Owner.Id || !container.Items.Contains(item) ||
            item.TemplateId != contract.ItemId || itemTemplate.NpcId != contract.NpcId ||
            itemTemplate.UseSkillId != contract.SkillId)
            return MateToggleResult.Rejected;

        var template = NpcManager.Instance.GetTemplate(contract.NpcId);
        if (template is null || template.ModelId == 0 || template.MateEquipSlotPackId <= 0 ||
            MateGameData.Instance.GetMateType((uint)template.MateEquipSlotPackId) == 0)
            return MateToggleResult.Rejected;

        // Resolve every dependency before withdrawing the current mate or allocating IDs.
        // A runtime DB drift must fail closed without changing the active lifecycle.
        var initialBuffs = template.Buffs
            .Select(SkillManager.Instance.GetBuffTemplate)
            .ToArray();
        if (initialBuffs.Any(buff => buff is null))
            return MateToggleResult.Rejected;

        var activeMates = Owner.ParentWorld.MateManager.GetActiveMates(Owner.Id).ToList();
        if (activeMates.Count > 0)
        {
            foreach (var oldMate in activeMates)
                DespawnMate(oldMate.TlId);
            return MateToggleResult.Despawned;
        }

        var recoveryState = MateGameData.Instance.GetRecoveryState(template.Id);
        var tlId = (ushort)TlIdManager.Instance.GetNextId();
        var objId = ObjectIdManager.Instance.GetNextId();
        var mateDbInfo = GetMateInfo(skillData.ItemId) ?? CreateNewMate(skillData.ItemId, template);
        if (mateDbInfo is null)
        {
            TlIdManager.Instance.ReleaseId(tlId);
            ObjectIdManager.Instance.ReleaseId(objId);
            return MateToggleResult.Rejected;
        }

        var mount = new Units.Mate
        {
            ObjId = objId,
            TlId = tlId,
            OwnerId = Owner.Id,
            Name = mateDbInfo.Name,
            TemplateId = contract.NpcId,
            Template = template,
            ModelId = template.ModelId,
            Faction = Owner.Faction,
            Level = (byte)mateDbInfo.Level,
            MateType = MateGameData.Instance.GetMateType((uint)template.MateEquipSlotPackId),
            // Replaced once the equipment bonuses are in and MaxHp/MaxMp are known, so that the
            // restore below clamps against the maximum the mate actually owns.
            Hp = 0,
            Mp = 0,
            OwnerObjId = Owner.ObjId,
            Id = mateDbInfo.Id,
            ItemId = mateDbInfo.ItemId,
            UserState = 1, // TODO
            Experience = mateDbInfo.Xp,
            Mileage = mateDbInfo.Mileage,
            SpawnDelayTime = 0, // TODO
            RecoveryState = recoveryState,
            DbInfo = mateDbInfo
        };

        mount.InitializeSeatTopology(MateGameData.Instance.GetMateSeats(contract.NpcId));

        mount.Transform = Owner.Transform.CloneDetached(mount);
        SusManager.Instance.ResetAnalyzeMountDeltaMovement(mount.Id);

        foreach (var skill in MateGameData.Instance.GetMateSkills(contract.NpcId))
            mount.Skills.Add(skill);

        foreach (var buff in initialBuffs)
        {
            var obj = new SkillCasterUnit(mount.ObjId);
            buff.Apply(mount, obj, mount, null, null, new EffectSource(), null, DateTime.UtcNow);
        }

        mount.Equipment = ItemManager.Instance.GetItemContainerForCharacter(Owner.Id, SlotType.EquipmentMate, mount, mount.Id);
        mount.UpdateGearBonuses(null, null);

        // What the owned row recorded is what the mate comes back with, bounded by the maximum its own
        // content reconstructs now that the gear bonuses are in. A row that never recorded a recovery
        // starts the mate at that maximum; a recorded one is kept, and cut down to the maximum when it
        // was saved against a larger one. Every recovery that lands afterwards — the regen tick, a
        // recovery item, a recovery skill — clamps against this same maximum.
        mount.Hp = MateRecoveryRules.RestorePoints(MateRecoveryRules.MateBar.Health, mateDbInfo.Hp, mount.MaxHp);
        mount.Mp = MateRecoveryRules.RestorePoints(MateRecoveryRules.MateBar.Mana, mateDbInfo.Mp, mount.MaxMp);

        mount.Transform.Local.AddDistanceToFront(3f);
        summonMate.DetailMateExp = mateDbInfo.Xp;
        summonMate.DetailLevel = checked((byte)mateDbInfo.Level);
        summonMate.IsDirty = true;
        //Logger.Warn($"Spawn the pet:{mount.ObjId} X={mount.Transform.World.Position.X} Y={mount.Transform.World.Position.Y}");
        Owner.ParentWorld.MateManager.AddActiveMateAndSpawn(Owner, mount, item);
        mount.PostUpdateCurrentHp(mount, 0, mount.Hp, KillReason.Unknown);

        // UnitState at spawn carries current Hp; gear MaxHealth is already in MaxHp. Re-push state
        // and points so the pet frame denominator matches server MaxHp (SCUnitPoints alone does not).
        UpdateMateInfo(skillData.ItemId, db =>
        {
            db.Hp = mount.Hp;
            db.Mp = mount.Mp;
        });
        Owner.SendPacket(new SCUnitStatePacket(mount));
        Owner.SendPacket(new SCUnitPointsPacket(mount.ObjId, mount.Hp, mount.Mp));
        WorldIntegration.RelayUnitPointsToZone?.Invoke(mount.ObjId, mount.Hp, mount.Mp);
        Owner.Buffs.TriggerRemoveOn(BuffRemoveOn.Summoned);
        return MateToggleResult.Spawned;
    }

    public bool RemoveByItemId(ulong itemId)
    {
        lock (_mateLifecycleLock)
            return RemoveByItemIdLocked(itemId);
    }

    private bool RemoveByItemIdLocked(ulong itemId)
    {
        if (!CanRemoveByItemIdLocked(itemId))
            return false;

        var activeMate = Owner.ParentWorld.MateManager.GetActiveMates(Owner.Id)
            .FirstOrDefault(mate => mate.ItemId == itemId);
        if (activeMate is not null)
            DespawnMate(activeMate.TlId);

        if (!_mates.Remove(itemId, out var mateDbInfo))
            return false;
        if (!_removedMates.Contains(mateDbInfo.Id))
            _removedMates.Add(mateDbInfo.Id);
        return true;
    }

    public bool CanRemoveByItemId(ulong itemId)
    {
        lock (_mateLifecycleLock)
            return CanRemoveByItemIdLocked(itemId);
    }

    private bool CanRemoveByItemIdLocked(ulong itemId)
    {
        var mateDbInfo = GetMateInfo(itemId);
        if (mateDbInfo is null)
            return true;
        var equipment = ItemManager.Instance.FindItemContainerFor(
            Owner.Id, SlotType.EquipmentMate, mateDbInfo.Id);
        return equipment is not { Items.Count: > 0 };
    }

    public void CapturePersistentState(Units.Mate mateInfo)
    {
        if (mateInfo is null)
            return;
        lock (_mateLifecycleLock)
            CapturePersistentStateLocked(mateInfo);
    }

    private void CapturePersistentStateLocked(Units.Mate mateInfo)
    {
        var mateDbInfo = GetMateInfo(mateInfo.ItemId);
        if (mateDbInfo is null)
            return;

        mateDbInfo.Capture(mateInfo, DateTime.UtcNow);

        if (Owner.Inventory?.GetItemById(mateInfo.ItemId) is SummonMate item)
        {
            item.DetailMateExp = mateInfo.Experience;
            item.DetailLevel = mateInfo.Level;
            item.IsDirty = true;
        }
    }

    /// <summary>
    /// Copies the live mate's persisted fields into its owned row so progress earned while
    /// summoned survives a despawn, a logout or the periodic save. Runs on gameplay threads
    /// (party kill, disconnect), so it must never fail because a save transaction is in flight.
    /// </summary>
    public void CaptureActiveMateState(Units.Mate mateInfo)
    {
        if (mateInfo == null)
            return;

        UpdateMateInfo(mateInfo.ItemId, mateDbInfo =>
        {
            mateDbInfo.Hp = mateInfo.Hp;
            mateDbInfo.Mp = mateInfo.Mp;
            mateDbInfo.Level = mateInfo.Level;
            mateDbInfo.Xp = mateInfo.Experience;
            mateDbInfo.Mileage = mateInfo.Mileage;
            mateDbInfo.Name = mateInfo.Name;
            mateDbInfo.UpdatedAt = DateTime.UtcNow;
        });
    }

    public void DespawnMate(uint tlId)
    {
        var mateInfo = Owner.ParentWorld.MateManager.GetActiveMateByTlId(tlId);
        if (mateInfo != null)
            CapturePersistentState(mateInfo);

        CaptureActiveMateState(mateInfo);
        Owner.ParentWorld.MateManager.RemoveActiveMateAndDespawn(Owner, tlId);
    }

    /// <summary>
    /// Load pet data of the player
    /// </summary>
    /// <param name="connection"></param>
    public void Load(DbConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM mates WHERE `owner` = @owner";
        AddParameter(command, "@owner", Owner.Id);
        command.Prepare();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var template = new MateDb
            {
                Id = Convert.ToUInt32(reader.GetValue(reader.GetOrdinal("id"))),
                ItemId = Convert.ToUInt64(reader.GetValue(reader.GetOrdinal("item_id"))),
                Name = reader.GetString("name"),
                Xp = reader.GetInt32("xp"),
                Level = Convert.ToUInt16(reader.GetValue(reader.GetOrdinal("level"))),
                Mileage = reader.GetInt32("mileage"),
                // NULL is "the row never held a bar"; 0 is a bar that really was empty. Reading a
                // missing column as 0 is what made a mate captured at zero come back at full health.
                Hp = ReadBar(reader, "hp"),
                Mp = ReadBar(reader, "mp"),
                Owner = Convert.ToUInt32(reader.GetValue(reader.GetOrdinal("owner"))),
                UpdatedAt = reader.GetDateTime("updated_at"),
                CreatedAt = reader.GetDateTime("created_at")
            };
            lock (_saveSync)
                _mates.Add(template.ItemId, template);
        }
    }

    /// <summary>
    /// Reads one recovery bar, mapping the column's NULL onto
    /// <see cref="MateRecoveryRules.Unrecorded"/> and leaving a real zero alone.
    /// </summary>
    private static int ReadBar(DbDataReader reader, string column)
    {
        var ordinal = reader.GetOrdinal(column);
        return reader.IsDBNull(ordinal)
            ? MateRecoveryRules.Unrecorded
            : reader.GetInt32(ordinal);
    }

    private static void AddParameter(DbCommand command, string name, object value)
    {
        var parameter = command.CreateParameter();
        parameter.ParameterName = name;
        parameter.Value = value;
        command.Parameters.Add(parameter);
    }

    /// <summary>
    /// Writes every owned mate row inside the caller's transaction. The snapshot is taken under
    /// the save lock, so a concurrent <see cref="UpdateMateInfo"/> is either included here or lands
    /// in the in-memory row that the next save writes; it is never rejected and never lost.
    /// </summary>
    public void Save(DbConnection connection, DbTransaction transaction)
    {
        ArgumentNullException.ThrowIfNull(connection);
        ArgumentNullException.ThrowIfNull(transaction);

        MateDb[] mateSnapshot;
        uint[] removedMates;
        lock (_saveSync)
        {
            mateSnapshot = _mates.Values.Select(mate => mate.Clone()).ToArray();
            removedMates = _removedMates.ToArray();
        }
        if (removedMates.Length > 0)
        {
            using var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = $"DELETE FROM mates WHERE owner = @owner AND id IN({string.Join(",", removedMates)})";
            AddParameter(command, "@owner", Owner.Id);
            command.ExecuteNonQuery();
            // Keep deletion intent until this character object is unloaded: rollback or retry is idempotent.
        }

        foreach (var value in mateSnapshot)
        {
            using var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText =
                "REPLACE INTO mates(`id`,`item_id`,`name`,`xp`,`level`,`mileage`,`hp`,`mp`,`owner`,`updated_at`,`created_at`) " +
                "VALUES (@id, @item_id, @name, @xp, @level, @mileage, @hp, @mp, @owner, @updated_at, @created_at)";
            AddParameter(command, "@id", value.Id);
            AddParameter(command, "@item_id", value.ItemId);
            AddParameter(command, "@name", value.Name);
            AddParameter(command, "@xp", value.Xp);
            AddParameter(command, "@level", value.Level);
            AddParameter(command, "@mileage", value.Mileage);
            AddParameter(command, "@hp", value.Hp == MateRecoveryRules.Unrecorded ? null : value.Hp);
            AddParameter(command, "@mp", value.Mp == MateRecoveryRules.Unrecorded ? null : value.Mp);
            AddParameter(command, "@owner", value.Owner);
            AddParameter(command, "@updated_at", value.UpdatedAt);
            AddParameter(command, "@created_at", value.CreatedAt);
            command.ExecuteNonQuery();
        }
    }
}

public class MateDb
{
    public uint Id { get; set; }
    public ulong ItemId { get; set; }
    public string Name { get; set; }
    public int Xp { get; set; }
    public ushort Level { get; set; }
    public int Mileage { get; set; }
    /// <summary>
    /// Health the mate was captured at, or <see cref="MateRecoveryRules.Unrecorded"/> when the row has
    /// never held one. Nullable so the database's NULL and a genuine zero stay different readings.
    /// </summary>
    public int Hp { get; set; }

    /// <summary>Mana, on the same footing as <see cref="Hp"/>.</summary>
    public int Mp { get; set; }
    public uint Owner { get; set; }
    public DateTime UpdatedAt { get; set; }
    public DateTime CreatedAt { get; set; }

    public void Capture(Units.Mate mate, DateTime updatedAt)
    {
        ArgumentNullException.ThrowIfNull(mate);
        Hp = mate.Hp;
        Mp = mate.Mp;
        Level = mate.Level;
        Xp = mate.Experience;
        Mileage = mate.Mileage;
        Name = mate.Name;
        UpdatedAt = updatedAt;
    }

    public MateDb Clone() => (MateDb)MemberwiseClone();
}
