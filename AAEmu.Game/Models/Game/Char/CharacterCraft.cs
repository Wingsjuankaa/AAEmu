using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Tasks.Skills;
using NLog;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// One active AA10 crafting session. Every requested unit is its own revalidated transaction;
/// backpack destination state is included in both pre-cast planning and the final commit.
/// </summary>
public class CharacterCraft
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly object _sessionLock = new();
    private readonly Character _owner;
    private readonly Func<CraftTask, TimeSpan, bool> _schedule;
    private readonly Func<int> _nextPercent;
    private Craft _currentCraft;
    private uint _doodadId;
    private int _remainingCount;
    private long _generation;
    private CraftTask _continuationTask;

    public CharacterCraft(Character owner)
        : this(
            owner,
            (task, delay) => TaskManager.Instance.Schedule(task, delay),
            () => Random.Shared.Next(100))
    {
    }

    internal CharacterCraft(Character owner, Func<CraftTask, TimeSpan, bool> schedule)
        : this(owner, schedule, () => Random.Shared.Next(100))
    {
    }

    internal CharacterCraft(
        Character owner,
        Func<CraftTask, TimeSpan, bool> schedule,
        Func<int> nextPercent)
    {
        _owner = owner ?? throw new ArgumentNullException(nameof(owner));
        _schedule = schedule ?? throw new ArgumentNullException(nameof(schedule));
        _nextPercent = nextPercent ?? throw new ArgumentNullException(nameof(nextPercent));
    }

    private Character Owner => _owner;

    public bool IsCrafting
    {
        get
        {
            lock (_sessionLock)
                return _currentCraft is not null;
        }
    }

    internal int RemainingCount
    {
        get
        {
            lock (_sessionLock)
                return _remainingCount;
        }
    }

    internal long Generation
    {
        get
        {
            lock (_sessionLock)
                return _generation;
        }
    }

    public bool TryStart(Craft craft, int count, uint doodadId)
    {
        lock (_sessionLock)
        {
            if (_currentCraft is not null)
                return Reject(new CraftFailure(CraftFailureCode.Busy));

            if (!TryPrepareUnit(craft, count, doodadId, out var prepared))
                return false;

            _currentCraft = craft;
            _doodadId = doodadId;
            _remainingCount = count;
            _generation++;
            return StartPreparedUnit(prepared);
        }
    }

    /// <summary>
    /// Runs a scheduled continuation only if it still belongs to the same active batch. A cancelled
    /// or replaced session invalidates the generation and makes every late task a no-op.
    /// </summary>
    internal bool TryContinue(uint craftId, uint doodadId, long generation)
    {
        lock (_sessionLock)
        {
            _continuationTask = null;
            if (_currentCraft is null || _currentCraft.Id != craftId || _doodadId != doodadId ||
                _generation != generation || _remainingCount <= 0)
                return false;

            if (!TryPrepareUnit(_currentCraft, 1, _doodadId, out var prepared))
            {
                ClearSession();
                return false;
            }
            return StartPreparedUnit(prepared);
        }
    }

    /// <summary>
    /// Revalidates and commits the active craft from its CraftEffect. A false result always cancels
    /// the source skill so labor, vocation and downstream interaction progress are not charged.
    /// </summary>
    public bool TryComplete(Skill sourceSkill, out uint craftId)
    {
        craftId = 0;
        lock (_sessionLock)
        {
            var craft = _currentCraft;
            var doodadId = _doodadId;
            if (craft is null)
                return CancelSource(sourceSkill, new CraftFailure(CraftFailureCode.RecipeUnavailable));

            if (sourceSkill?.Template is null || sourceSkill.Template.Id != craft.SkillId ||
                !sourceSkill.Template.Effects.Any(effect => effect.Template is CraftEffect))
                return CancelAndClear(sourceSkill, new CraftFailure(CraftFailureCode.SkillRejected));

            sourceSkill.SkipAutomaticItemConsumption = true;
            if (!TryValidateStation(craft, doodadId, out var stationFailure))
                return CancelAndClear(sourceSkill, stationFailure);

            var laborCost = sourceSkill.CalculateLaborCost(Owner);
            if (laborCost < 0 || laborCost > short.MaxValue ||
                Owner.LaborPower + Owner.LocalLaborPower < laborCost)
                return CancelAndClear(sourceSkill, new CraftFailure(CraftFailureCode.NotEnoughLabor));

            if (!TryPlan(craft, 1, sourceSkill.Template, true, out var plan, out var failure))
                return CancelAndClear(sourceSkill, failure);

            var consumeTasks = new List<ItemTask>();
            var rewardTasks = new List<ItemTask>();
            var forceRemove = new List<ulong>();
            if (!Owner.TryCommitCraftTransaction(
                    plan, laborCost, sourceSkill.Template.ActabilityGroupId,
                    consumeTasks, forceRemove, rewardTasks, out var moneyTask, out failure))
                return CancelAndClear(sourceSkill, failure);

            craftId = craft.Id;
            // Labor and its actability/quest side effects are part of the transaction above.
            // EndSkill still owns vocation and lifecycle packets, but must not charge this unit twice.
            sourceSkill.LaborCostUnits = 0;
            _remainingCount--;

            foreach (var packet in ItemContainer.BuildIndependentItemTaskPackets(
                         ItemTaskType.CraftActSaved, consumeTasks, forceRemove))
                Owner.SendPacket(packet);
            if (moneyTask is not null)
                Owner.SendPacket(new SCItemTaskSuccessPacket(
                    ItemTaskType.CraftPaySaved, moneyTask, []));
            foreach (var task in rewardTasks)
                Owner.SendPacket(new SCItemTaskSuccessPacket(
                    ItemTaskType.CraftPickupProduct, task, []));
            if (plan.FailedProductItemIds.Count > 0)
                Owner.SendPacket(new SCCraftFailedPacket(
                    unchecked((int)craft.Id), plan.FailedProductItemIds));

            QuestManager.Instance.DoOnCraftEvents(Owner, craft.Id);

            var remaining = _remainingCount;
            if (remaining > 0)
            {
                var continuation = new CraftTask(Owner, craft.Id, doodadId, _generation);
                _continuationTask = continuation;
                if (!_schedule(continuation, TimeSpan.FromMilliseconds(plan.CastDelay)))
                {
                    Logger.Error(
                        "Could not schedule AA10 craft continuation: character={0}, craft={1}, remaining={2}",
                        Owner.Id, craft.Id, remaining);
                    ClearSession();
                }
            }
            else
            {
                ClearSession();
            }

            Logger.Info(
                "AA10 craft committed: character={0}, craft={1}, station={2}, materials={3}, products={4}, failedProducts={5}, cost={6}, labor={7}, remaining={8}",
                Owner.Id, craft.Id, doodadId, plan.Materials.Count, plan.Products.Count,
                plan.FailedProductItemIds.Count, plan.MoneyCost, laborCost, remaining);
            return true;
        }
    }

    public void Cancel()
    {
        lock (_sessionLock)
        {
            if (_currentCraft is null)
                return;
            if (Owner.SkillTask?.Skill is { } skill)
                skill.Cancelled = true;
            ClearSession();
        }
    }

    /// <summary>
    /// Releases the crafting session only when the cancelled skill belongs to that session. This
    /// prevents a late CSStopCasting for an older timeline from clearing a newer craft.
    /// </summary>
    public bool Cancel(Skill sourceSkill)
    {
        lock (_sessionLock)
        {
            if (_currentCraft is null || sourceSkill?.Template is null ||
                sourceSkill.Template.Id != _currentCraft.SkillId)
                return false;

            sourceSkill.SkipAutomaticItemConsumption = true;
            sourceSkill.Cancelled = true;
            ClearSession();
            return true;
        }
    }

    private bool TryPrepareUnit(Craft craft, int count, uint doodadId, out PreparedCraftUnit prepared)
    {
        prepared = null;
        var skillTemplate = craft is null ? null : SkillManager.Instance.GetSkillTemplate(craft.SkillId);
        var hasCraftEffect = skillTemplate?.Effects.Any(effect => effect.Template is CraftEffect) == true;
        var actabilityGroupId = skillTemplate?.ActabilityGroupId > 0
            ? (uint)skillTemplate.ActabilityGroupId
            : 0;
        if (!CraftTransactionPlanner.TryValidateContract(
                craft, count, ResolveItem, skillTemplate is not null, hasCraftEffect,
                actabilityGroupId, out _, out var contractFailure))
        {
            if (craft is null || skillTemplate is null)
                return Reject(contractFailure);

            var failedSkill = new Skill(skillTemplate);
            var failedCaster = SkillCaster.GetByType(SkillCasterType.Unit);
            failedCaster.ObjId = Owner.ObjId;
            var failedTarget = SkillCastTarget.GetByType(SkillCastTargetType.Doodad);
            failedTarget.ObjId = doodadId;
            return RejectBeforeSkillStart(
                craft, failedSkill, failedCaster, failedTarget, new SkillObject(), contractFailure);
        }

        var skill = new Skill(skillTemplate);
        var caster = SkillCaster.GetByType(SkillCasterType.Unit);
        caster.ObjId = Owner.ObjId;
        var target = SkillCastTarget.GetByType(SkillCastTargetType.Doodad);
        target.ObjId = doodadId;
        var skillObject = new SkillObject();

        if (!TryValidateStation(craft, doodadId, out var stationFailure))
            return RejectBeforeSkillStart(craft, skill, caster, target, skillObject, stationFailure);
        if (!TryPlan(craft, count, skillTemplate, false, out _, out var planFailure))
            return RejectBeforeSkillStart(craft, skill, caster, target, skillObject, planFailure);

        var laborCost = skill.CalculateLaborCost(Owner);
        if (laborCost < 0 || laborCost > short.MaxValue ||
            Owner.LaborPower + Owner.LocalLaborPower < laborCost)
            return RejectBeforeSkillStart(
                craft, skill, caster, target, skillObject,
                new CraftFailure(CraftFailureCode.NotEnoughLabor));

        prepared = new PreparedCraftUnit(skill, caster, target, skillObject);
        return true;
    }

    private bool StartPreparedUnit(PreparedCraftUnit prepared)
    {
        var craft = _currentCraft;
        var result = prepared.Skill.Use(
            Owner, prepared.Caster, prepared.Target, prepared.SkillObject, false,
            out var resultValueUShort, out var resultValueUInt);
        if (result == SkillResult.Success)
            return true;

        ClearSession();
        SendSkillStartFailure(
            prepared.Skill, prepared.Caster, prepared.Target, prepared.SkillObject,
            result, resultValueUShort, resultValueUInt);
        Logger.Warn(
            "Rejected AA10 craft skill start: character={0}, craft={1}, skill={2}, result={3}",
            Owner.Id, craft?.Id ?? 0, prepared.Skill.Id, result);
        return false;
    }

    private bool TryPlan(
        Craft craft,
        int count,
        SkillTemplate skillTemplate,
        bool resolveRates,
        out CraftTransactionPlan plan,
        out CraftFailure failure)
    {
        var bag = Owner.Inventory.Bag;
        var equipment = Owner.Inventory.Equipment;
        CraftInventorySnapshot inventory;
        lock (bag.Items)
        lock (equipment.Items)
        {
            var equippedBackpack = equipment.GetItemBySlot((int)EquipmentItemSlot.Backpack);
            var backpackSlot = equippedBackpack switch
            {
                null => CraftBackpackSlotState.Empty,
                { Template: BackpackTemplate { BackpackType: BackpackType.Glider } } =>
                    CraftBackpackSlotState.Glider,
                _ => CraftBackpackSlotState.Occupied
            };
            inventory = new CraftInventorySnapshot(
                bag.FreeSlotCount,
                bag.Items.OrderBy(item => item.Slot).Select(item => new CraftInventoryStack(
                    item.TemplateId, item.Count, item.Grade, item.CanDestroy())).ToArray(),
                backpackSlot,
                Owner.Buffs.HasEffectsMatchingCondition(effect => effect.Template.Gliding));
        }

        var actabilityGroupId = skillTemplate?.ActabilityGroupId > 0
            ? (uint)skillTemplate.ActabilityGroupId
            : 0;
        var actabilityPoints = actabilityGroupId == 0
            ? 0
            : Owner.Actability.GetPoint(actabilityGroupId, !craft.UseOnlyActability);
        var economy = new CraftEconomySnapshot(Owner.Money, actabilityPoints);
        IReadOnlyList<int> productRolls = null;
        if (resolveRates)
        {
            var probabilisticProducts = craft.CraftProducts.Count(product => product.Rate == 50);
            if (probabilisticProducts > 0)
                productRolls = Enumerable.Range(0, probabilisticProducts)
                    .Select(_ => _nextPercent()).ToArray();
        }
        return CraftTransactionPlanner.TryCreate(
            craft, count, inventory, economy, ResolveItem, skillTemplate is not null,
            skillTemplate?.Effects.Any(effect => effect.Template is CraftEffect) == true,
            actabilityGroupId, productRolls, out plan, out failure);
    }

    private static CraftItemDefinition ResolveItem(uint itemId)
    {
        var template = ItemManager.Instance.GetTemplate(itemId);
        return CraftItemDefinition.FromTemplate(
            template,
            template is not null && ItemManager.Instance.IsAutoEquipTradePack(itemId));
    }

    private bool TryValidateStation(Craft craft, uint doodadId, out CraftFailure failure)
    {
        var doodad = Owner.ParentWorld?.GetDoodad(doodadId);
        return CraftStationValidator.TryValidate(
            craft, doodad is not null, doodad?.TemplateId ?? 0, doodad?.FuncPermission,
            out failure);
    }

    private bool CancelAndClear(Skill skill, CraftFailure failure)
    {
        ClearSession();
        return CancelSource(skill, failure);
    }

    private bool CancelSource(Skill skill, CraftFailure failure)
    {
        if (skill is not null)
        {
            skill.SkipAutomaticItemConsumption = true;
            skill.Cancelled = true;
        }
        return Reject(failure);
    }

    private bool RejectBeforeSkillStart(
        Craft craft,
        Skill skill,
        SkillCaster caster,
        SkillCastTarget target,
        SkillObject skillObject,
        CraftFailure failure)
    {
        var result = failure.Code switch
        {
            CraftFailureCode.StationUnavailable or CraftFailureCode.PermissionDenied => SkillResult.NoPerm,
            CraftFailureCode.NotEnoughLabor => SkillResult.NeedLaborPower,
            CraftFailureCode.NotEnoughMoney => SkillResult.NeedMoney,
            CraftFailureCode.NotEnoughActability => SkillResult.LackActability,
            CraftFailureCode.MissingMaterials => SkillResult.NeedReagent,
            CraftFailureCode.ItemNotDestroyable => SkillResult.ItemLocked,
            CraftFailureCode.BagFull => SkillResult.BagFull,
            CraftFailureCode.BackpackOccupied or CraftFailureCode.CannotChangeBackpackInGliding =>
                SkillResult.BackpackOccupied,
            _ => SkillResult.Failure
        };
        SendSkillStartFailure(skill, caster, target, skillObject, result, 0, 0);
        Logger.Warn(
            "Rejected AA10 craft before skill start: character={0}, craft={1}, skill={2}, failure={3}, blocker={4}, result={5}",
            Owner.Id, craft.Id, skill.Id, failure.Code, failure.BlockReason, result);
        return false;
    }

    private void SendSkillStartFailure(
        Skill skill,
        SkillCaster caster,
        SkillCastTarget target,
        SkillObject skillObject,
        SkillResult result,
        ushort resultValueUShort,
        uint resultValueUInt)
    {
        var packet = new SCSkillStartedPacket(
            skill.Id, 0, caster, target, skill, skillObject)
        {
            RealCastTimeMs = 0,
            BaseCastTimeMs = 0
        };
        packet.SetSkillResult(result);
        packet.SetResultUShort(resultValueUShort);
        packet.SetResultUInt(resultValueUInt);
        Owner.SendPacket(packet);
    }

    private bool Reject(CraftFailure failure)
    {
        var error = failure.Code switch
        {
            CraftFailureCode.StationUnavailable or CraftFailureCode.PermissionDenied =>
                ErrorMessageType.CraftPermissionDeny,
            CraftFailureCode.NotEnoughLabor => ErrorMessageType.NotEnoughLaborPower,
            CraftFailureCode.NotEnoughMoney => ErrorMessageType.NotEnoughMoney,
            CraftFailureCode.NotEnoughActability => ErrorMessageType.ActabilityNotEnoughPoint,
            CraftFailureCode.MissingMaterials => ErrorMessageType.NotEnoughRequiredItem,
            CraftFailureCode.ItemNotDestroyable => ErrorMessageType.ItemLocked,
            CraftFailureCode.BagFull => ErrorMessageType.BagFull,
            CraftFailureCode.BackpackOccupied => ErrorMessageType.BackpackOccupied,
            CraftFailureCode.CannotChangeBackpackInGliding =>
                ErrorMessageType.CannotChangeBackpackInGliding,
            _ => ErrorMessageType.CraftCantActAnyMore
        };
        Owner.SendErrorMessage(error);
        Logger.Warn(
            "Rejected AA10 craft: character={0}, failure={1}, blocker={2}",
            Owner.Id, failure.Code, failure.BlockReason);
        return false;
    }

    private void ClearSession()
    {
        _generation++;
        if (_continuationTask is not null)
            _continuationTask.Cancelled = true;
        _continuationTask = null;
        _currentCraft = null;
        _doodadId = 0;
        _remainingCount = 0;
    }

    private sealed record PreparedCraftUnit(
        Skill Skill,
        SkillCaster Caster,
        SkillCastTarget Target,
        SkillObject SkillObject);
}
