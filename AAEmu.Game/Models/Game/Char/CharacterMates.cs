using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units.Static;

using MySql.Data.MySqlClient;

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

    private readonly object _mateLifecycleLock = new();
    private readonly Dictionary<ulong, MateDb> _mates = []; // itemId, MountDb
    private readonly List<uint> _removedMates = [];

    public MateDb GetMateInfo(ulong itemId)
    {
        return _mates.GetValueOrDefault(itemId);
    }

    private MateDb CreateNewMate(ulong itemId, NpcTemplate npcTemplate)
    {
        if (_mates.ContainsKey(itemId)) return null;
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
            Hp = 9999,
            Mp = 9999,
            UpdatedAt = DateTime.UtcNow,
            CreatedAt = DateTime.UtcNow
        };
        _mates.Add(template.ItemId, template);
        return template;
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
            Hp = mateDbInfo.Hp > 0 ? mateDbInfo.Hp : 100,
            Mp = mateDbInfo.Mp > 0 ? mateDbInfo.Mp : 100,
            OwnerObjId = Owner.ObjId,
            Id = mateDbInfo.Id,
            ItemId = mateDbInfo.ItemId,
            UserState = 1, // TODO
            Experience = mateDbInfo.Xp,
            Mileage = mateDbInfo.Mileage,
            SpawnDelayTime = 0, // TODO
            DbInfo = mateDbInfo
        };

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

        // CreateNewMate seeds Hp/Mp at 9999 as "full"; after MaxHp is known, treat that sentinel
        // (or any over-cap) as full so the pet frame does not spawn mid-bar waiting on regen.
        if (mateDbInfo.Hp >= 9999 || mount.Hp >= mount.MaxHp)
            mount.Hp = mount.MaxHp;
        else
            mount.Hp = Math.Min(mount.Hp, mount.MaxHp);
        if (mateDbInfo.Mp >= 9999 || mount.Mp >= mount.MaxMp)
            mount.Mp = mount.MaxMp;
        else
            mount.Mp = Math.Min(mount.Mp, mount.MaxMp);

        mount.Transform.Local.AddDistanceToFront(3f);
        summonMate.DetailMateExp = mateDbInfo.Xp;
        summonMate.DetailLevel = checked((byte)mateDbInfo.Level);
        summonMate.IsDirty = true;
        //Logger.Warn($"Spawn the pet:{mount.ObjId} X={mount.Transform.World.Position.X} Y={mount.Transform.World.Position.Y}");
        Owner.ParentWorld.MateManager.AddActiveMateAndSpawn(Owner, mount, item);
        mount.PostUpdateCurrentHp(mount, 0, mount.Hp, KillReason.Unknown);

        // UnitState at spawn carries current Hp; gear MaxHealth is already in MaxHp. Re-push state
        // and points so the pet frame denominator matches server MaxHp (SCUnitPoints alone does not).
        mateDbInfo.Hp = mount.Hp;
        mateDbInfo.Mp = mount.Mp;
        Owner.SendPacket(new SCUnitStatePacket(mount));
        Owner.SendPacket(new SCUnitPointsPacket(mount.ObjId, mount.Hp, mount.Mp));
        WorldIntegration.RelayUnitPointsToZone?.Invoke(mount.ObjId, mount.Hp, mount.Mp);
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

        if (Owner.Inventory.GetItemById(mateInfo.ItemId) is SummonMate item)
        {
            item.DetailMateExp = mateInfo.Experience;
            item.DetailLevel = mateInfo.Level;
            item.IsDirty = true;
        }
    }

    public void DespawnMate(uint tlId)
    {
        var mateInfo = Owner.ParentWorld.MateManager.GetActiveMateByTlId(tlId);
        if (mateInfo != null)
            CapturePersistentState(mateInfo);

        Owner.ParentWorld.MateManager.RemoveActiveMateAndDespawn(Owner, tlId);
    }

    /// <summary>
    /// Load pet data of the player
    /// </summary>
    /// <param name="connection"></param>
    public void Load(MySqlConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM mates WHERE `owner` = @owner";
        command.Parameters.AddWithValue("@owner", Owner.Id);
        command.Prepare();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            var template = new MateDb
            {
                Id = reader.GetUInt32("id"),
                ItemId = reader.GetUInt64("item_id"),
                Name = reader.GetString("name"),
                Xp = reader.GetInt32("xp"),
                Level = reader.GetUInt16("level"),
                Mileage = reader.GetInt32("mileage"),
                Hp = reader.GetInt32("hp"),
                Mp = reader.GetInt32("mp"),
                Owner = reader.GetUInt32("owner"),
                UpdatedAt = reader.GetDateTime("updated_at"),
                CreatedAt = reader.GetDateTime("created_at")
            };
            _mates.Add(template.ItemId, template);
        }
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        if (_removedMates.Count > 0)
        {
            using var command = connection.CreateCommand();
            command.Connection = connection;
            command.Transaction = transaction;

            command.CommandText = $"DELETE FROM mates WHERE owner = @owner AND id IN({string.Join(",", _removedMates)})";
            command.Parameters.AddWithValue("@owner", Owner.Id);
            command.Prepare();
            command.ExecuteNonQuery();
            _removedMates.Clear();
        }

        foreach (var (_, value) in _mates)
        {
            using var command = connection.CreateCommand();
            command.Connection = connection;
            command.Transaction = transaction;

            command.CommandText =
                "REPLACE INTO mates(`id`,`item_id`,`name`,`xp`,`level`,`mileage`,`hp`,`mp`,`owner`,`updated_at`,`created_at`) " +
                "VALUES (@id, @item_id, @name, @xp, @level, @mileage, @hp, @mp, @owner, @updated_at, @created_at)";
            command.Parameters.AddWithValue("@id", value.Id);
            command.Parameters.AddWithValue("@item_id", value.ItemId);
            command.Parameters.AddWithValue("@name", value.Name);
            command.Parameters.AddWithValue("@xp", value.Xp);
            command.Parameters.AddWithValue("@level", value.Level);
            command.Parameters.AddWithValue("@mileage", value.Mileage);
            command.Parameters.AddWithValue("@hp", value.Hp);
            command.Parameters.AddWithValue("@mp", value.Mp);
            command.Parameters.AddWithValue("@owner", value.Owner);
            command.Parameters.AddWithValue("@updated_at", value.UpdatedAt);
            command.Parameters.AddWithValue("@created_at", value.CreatedAt);
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
    public int Hp { get; set; }
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
}
