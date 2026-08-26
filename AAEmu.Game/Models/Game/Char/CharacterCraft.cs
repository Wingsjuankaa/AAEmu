using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using NLog;

namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// One active AA10 crafting session. Wave 1 executes exactly one recipe unit and fails closed for
/// every contract that has not yet passed its native-evidence gate.
/// </summary>
public class CharacterCraft(Character owner)
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly object _sessionLock = new();
    private Craft _currentCraft;
    private uint _doodadId;

    private Character Owner => owner;

    public bool IsCrafting
    {
        get
        {
            lock (_sessionLock)
                return _currentCraft is not null;
        }
    }

    public bool TryStart(Craft craft, int count, uint doodadId)
    {
        lock (_sessionLock)
        {
            if (_currentCraft is not null)
                return Reject(new CraftFailure(CraftFailureCode.Busy));

            var skillTemplate = craft is null ? null : SkillManager.Instance.GetSkillTemplate(craft.SkillId);
            var hasCraftEffect = skillTemplate?.Effects.Any(effect => effect.Template is CraftEffect) == true;
            if (!CraftTransactionPlanner.TryValidateContract(
                    craft, count, ResolveItem, skillTemplate is not null, hasCraftEffect,
                    out _, out var contractFailure))
                return Reject(contractFailure);

            var skill = new Skill(skillTemplate);
            var caster = SkillCaster.GetByType(SkillCasterType.Unit);
            caster.ObjId = Owner.ObjId;
            var target = SkillCastTarget.GetByType(SkillCastTargetType.Doodad);
            target.ObjId = doodadId;
            var skillObject = new SkillObject();

            // ExecuteBatchCraftByType has already marked the native client manager as working.
            // A plain SCErrorMsg leaves that flag set, while a failed SkillStarted (tl=0) follows
            // the r575 event-0x16 branch that resets the batch without publishing CRAFT_STARTED.
            if (!TryValidateStation(craft, doodadId, out var stationFailure))
                return RejectBeforeSkillStart(craft, skill, caster, target, skillObject, stationFailure);
            if (!TryPlan(craft, count, true, true, out _, out var planFailure))
                return RejectBeforeSkillStart(craft, skill, caster, target, skillObject, planFailure);

            var laborCost = skill.CalculateLaborCost(Owner);
            if (laborCost < 0 || laborCost > short.MaxValue ||
                Owner.LaborPower + Owner.LocalLaborPower < laborCost)
                return RejectBeforeSkillStart(
                    craft, skill, caster, target, skillObject,
                    new CraftFailure(CraftFailureCode.NotEnoughLabor));

            _currentCraft = craft;
            _doodadId = doodadId;

            var result = skill.Use(
                Owner, caster, target, skillObject, false,
                out var resultValueUShort, out var resultValueUInt);
            if (result == SkillResult.Success)
                return true;

            ClearSession();
            SendSkillStartFailure(
                skill, caster, target, skillObject, result, resultValueUShort, resultValueUInt);
            Logger.Warn(
                "Rejected AA10 craft skill start: character={0}, craft={1}, skill={2}, result={3}",
                Owner.Id, craft.Id, craft.SkillId, result);
            return false;
        }
    }

    /// <summary>
    /// Revalidates and commits the active craft from its CraftEffect. A false result always cancels
    /// the source skill so labor, vocation and downstream interaction progress are not charged.
    /// </summary>
    public bool TryComplete(Skill sourceSkill, out uint craftId)
    {
        craftId = 0;
        Craft craft;
        uint doodadId;
        lock (_sessionLock)
        {
            craft = _currentCraft;
            doodadId = _doodadId;
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

            var bag = Owner.Inventory.Bag;
            var consumeTasks = new List<ItemTask>();
            var rewardTasks = new List<ItemTask>();
            var forceRemove = new List<ulong>();
            CraftTransactionPlan plan;
            CraftFailure failure;

            lock (bag.Items)
            {
                if (!TryPlan(craft, 1, true, true, out plan, out failure) ||
                    !bag.TryExchangeCraftItems(
                        plan, Owner.Id, consumeTasks, forceRemove, rewardTasks, out failure))
                    return CancelAndClear(sourceSkill, failure);
            }

            ClearSession();
            craftId = craft.Id;
            sourceSkill.LaborCostUnits = 1;

            foreach (var packet in ItemContainer.BuildIndependentItemTaskPackets(
                         ItemTaskType.CraftActSaved, consumeTasks, forceRemove))
                Owner.SendPacket(packet);
            foreach (var task in rewardTasks)
                Owner.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.CraftActSaved, task, []));

            QuestManager.Instance.DoOnCraftEvents(Owner, craft.Id);
            Logger.Info(
                "AA10 craft committed: character={0}, craft={1}, station={2}, materials={3}, products={4}, labor={5}",
                Owner.Id, craft.Id, doodadId, plan.Materials.Count, plan.Products.Count, laborCost);
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
    /// prevents a late CSStopCasting for an older or unrelated timeline from clearing a newer
    /// craft while still guaranteeing that a cancelled craft can be started again immediately.
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

    private bool TryPlan(
        Craft craft,
        int count,
        bool hasCraftSkill,
        bool hasCraftEffect,
        out CraftTransactionPlan plan,
        out CraftFailure failure)
    {
        var bag = Owner.Inventory.Bag;
        CraftInventorySnapshot snapshot;
        lock (bag.Items)
        {
            snapshot = new CraftInventorySnapshot(
                bag.FreeSlotCount,
                bag.Items.OrderBy(item => item.Slot).Select(item => new CraftInventoryStack(
                    item.TemplateId,
                    item.Count,
                    item.Grade,
                    item.CanDestroy())).ToArray());
        }

        return CraftTransactionPlanner.TryCreate(
            craft,
            count,
            snapshot,
            ResolveItem,
            hasCraftSkill,
            hasCraftEffect,
            out plan,
            out failure);
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
            craft,
            doodad is not null,
            doodad?.TemplateId ?? 0,
            doodad?.FuncPermission,
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
            CraftFailureCode.MissingMaterials => SkillResult.NeedReagent,
            CraftFailureCode.ItemNotDestroyable => SkillResult.ItemLocked,
            CraftFailureCode.BagFull => SkillResult.BagFull,
            _ => SkillResult.Failure
        };
        SendSkillStartFailure(skill, caster, target, skillObject, result, 0, 0);
        Logger.Warn(
            "Rejected AA10 craft before skill start: character={0}, craft={1}, skill={2}, failure={3}, blocker={4}, result={5}",
            Owner.Id, craft.Id,
            skill.Id, failure.Code, failure.BlockReason, result);
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
            CraftFailureCode.MissingMaterials => ErrorMessageType.NotEnoughRequiredItem,
            CraftFailureCode.ItemNotDestroyable => ErrorMessageType.ItemLocked,
            CraftFailureCode.BagFull => ErrorMessageType.BagFull,
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
        _currentCraft = null;
        _doodadId = 0;
    }
}
