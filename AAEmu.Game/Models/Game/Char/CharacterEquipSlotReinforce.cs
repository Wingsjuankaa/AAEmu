using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using MySql.Data.MySqlClient;
using NLog;

namespace AAEmu.Game.Models.Game.Char;

public sealed class CharacterEquipSlotReinforce(Character owner)
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
    private readonly object _sync = new();
    private EquipSlotReinforceState _state = new();
    private IReadOnlyList<Bonus> _bonuses = [];
    public EquipSlotReinforceState Snapshot => Volatile.Read(ref _state);
    public IReadOnlyList<Bonus> Bonuses => IsEnabled ? Volatile.Read(ref _bonuses) : [];
    private static EquipSlotReinforceGameData Data => EquipSlotReinforceGameData.Instance;
    public static bool IsEnabled => FeaturesManager.Fsets?.Check(Feature.equipSlotEnchantment) == true;

    public double GetItemLevelGain(byte slot, int itemLevel)
    {
        if (!IsEnabled || !Data.Levels.TryGetValue((slot, Snapshot.Get(slot).Level), out var level))
            return 0;
        if (!Data.UseItemLevelFormula) return level.GainItemLevel;
        var formula = FormulaManager.Instance.GetFormula(69) ??
            throw new InvalidOperationException("Missing native Ipnya formula69.");
        return formula.Evaluate(new Dictionary<string, double>
        {
            ["item_level"] = itemLevel, ["gain_item_level"] = level.GainItemLevel
        });
    }

    public void Load(MySqlConnection connection)
    {
        var slots = new Dictionary<byte, EquipSlotReinforceProgress>();
        var effects = new Dictionary<EquipSlotReinforceEffectKey, uint>();
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT slot,level,experience FROM character_equip_slot_reinforces WHERE owner=@owner";
            command.Parameters.AddWithValue("@owner", owner.Id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var slot = reader.GetByte("slot"); var level = reader.GetSByte("level");
                var experience = reader.GetInt32("experience");
                if (!Data.Levels.TryGetValue((slot, level), out var descriptor) || experience < 0 ||
                    experience > descriptor.RequiredExperience)
                    throw new InvalidDataException($"Invalid persisted Ipnya slot {owner.Id}/{slot}/{level}.");
                slots.Add(slot, new(level, experience));
            }
        }
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT slot,level,modifier FROM character_equip_slot_reinforce_effects WHERE owner=@owner";
            command.Parameters.AddWithValue("@owner", owner.Id);
            using var reader = command.ExecuteReader();
            while (reader.Read())
            {
                var key = new EquipSlotReinforceEffectKey(reader.GetByte("slot"), reader.GetSByte("level"));
                var id = reader.GetUInt32("modifier");
                if (!slots.TryGetValue(key.Slot, out var progress) || key.Level > progress.Level ||
                    !Data.Modifiers.TryGetValue(id, out var modifier) ||
                    !Data.Milestones.TryGetValue(modifier.Milestone, out var milestone) ||
                    milestone.Slot != key.Slot || milestone.Level != key.Level)
                    throw new InvalidDataException($"Invalid persisted Ipnya effect {owner.Id}/{key}/{id}.");
                effects.Add(key, id);
            }
        }
        SetState(new(slots, effects));
    }

    public bool AddExperience(byte slot, uint material, bool useAaPoint) =>
        Commit(state => EquipSlotReinforceCalculator.AddExperience(Data, state, slot, material, useAaPoint));
    public bool LevelUp(byte slot) =>
        Commit(state => EquipSlotReinforceCalculator.LevelUp(Data, state, slot, Random.Shared.Next));
    public bool ChangeEffect(byte slot, sbyte level) =>
        Commit(state => EquipSlotReinforceCalculator.ChangeEffect(Data, state, slot, level, Random.Shared.Next));

    private bool Commit(Func<EquipSlotReinforceState, EquipSlotReinforcePlan> makePlan)
    {
        List<ItemTask> tasks = []; List<ulong> removals = [];
        EquipSlotReinforcePlan plan;
        lock (GamePersistence.Sync)
        lock (_sync)
        {
            if (!IsEnabled || owner.Level < Data.MinimumLevel || owner.Hp <= 0)
                return Reject();
            plan = makePlan(_state);
            if (plan is null) return Reject();
            try
            {
                if (!owner.TryCommitEquipSlotReinforce(plan, tasks, removals,
                        (items, gold, aaPoint) => { Persist(plan, items, gold, aaPoint); SetState(plan.State); }))
                    return Reject();
            }
            catch (Exception exception)
            {
                Logger.Error(exception, "Ipnya transaction failed for character {0}", owner.Id);
                return Reject();
            }
        }
        // The operation is already durable. Publish a single inventory transaction before progress.
        owner.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.ConsumeSkillSource, tasks, removals));
        var progress = plan.State.Get(plan.Slot);
        owner.BroadcastPacket(new SCEquipSlotReinforceUpdatePacket(owner.ObjId, plan.Slot, progress.Level,
            progress.Experience), true);
        if (plan.ChangedEffect is { } key)
            owner.BroadcastPacket(new SCEquipSlotReinforceLevelEffectUpdatePacket(owner.ObjId, key.Slot,
                key.Level, plan.ModifierId), true);
        owner.Hp = Math.Min(owner.Hp, owner.MaxHp);
        owner.Mp = Math.Min(owner.Mp, owner.MaxMp);
        owner.BroadcastPacket(new SCUnitPointsPacket(owner.ObjId, owner.Hp, owner.Mp), true);
        if (WorldIntegration.ZoneAuthority)
            WorldIntegration.RelayUnitPointsToZone?.Invoke(owner.ObjId, owner.Hp, owner.Mp);
        Logger.Info("Ipnya committed character={0} slot={1} level={2} exp={3} effect={4}",
            owner.Id, plan.Slot, progress.Level, progress.Experience, plan.ModifierId);
        return true;
    }

    private bool Reject()
    {
        owner.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
        return false;
    }

    private void SetState(EquipSlotReinforceState state)
    {
        Volatile.Write(ref _state, state);
        Volatile.Write(ref _bonuses, EquipSlotReinforceCalculator.GetBonuses(Data, state));
    }

    private void Persist(EquipSlotReinforcePlan plan, IReadOnlyCollection<(Item Item, int Amount)> items,
        long gold, long aaPoint)
    {
        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        using (var exists = connection.CreateCommand())
        {
            exists.Transaction = transaction;
            exists.CommandText = "SELECT id FROM characters WHERE id=@owner FOR UPDATE";
            exists.Parameters.AddWithValue("@owner", owner.Id);
            if (exists.ExecuteScalar() is null)
                throw new InvalidOperationException("Ipnya owner is not persisted.");
        }
        foreach (var (item, amount) in items)
            EquipSlotReinforceRepository.SaveConsumedItem(connection, transaction, item, amount);
        using (var command = connection.CreateCommand())
        {
            command.Transaction = transaction;
            command.CommandText = "UPDATE characters SET money=@gold,aa_point=@aa WHERE id=@owner";
            command.Parameters.AddWithValue("@gold", gold); command.Parameters.AddWithValue("@aa", aaPoint);
            command.Parameters.AddWithValue("@owner", owner.Id);
            command.ExecuteNonQuery();
        }
        EquipSlotReinforceRepository.SaveState(connection, transaction, owner.Id, plan.State);
        transaction.Commit();
    }
}
