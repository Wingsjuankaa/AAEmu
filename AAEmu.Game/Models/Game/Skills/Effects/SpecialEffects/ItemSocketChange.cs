using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Socket change (special effect type 169): a conversion or upgrade stone turns the lunagems already
/// seated in a piece into other lunagems. No roll, and the other sockets are left alone.
/// </summary>
/// <remarks>
/// <para>
/// The stone's use-skill casts with the stone as the item caster and the piece as the item target,
/// the same shape lunagem seating uses. <c>item_socket_changes</c> says, per stone, which seated
/// gem becomes which. The gear window's upgrade tab only lets the player tick sockets whose gem the
/// stone can change, and sends the ticked ones as a bit mask in the cast's first extra value, bit N
/// for socket N.
/// </para>
/// <para>
/// One stone and <c>value1</c> labor (200 on every shipped stone) per changed socket. The labor is
/// what the stone's description says and what the tab shows next to its button. The stone count
/// comes from the tab itself, which stops taking ticks once they equal the stones in the bag. The
/// stones are not <c>use_skill_as_reagent</c> and their skill rows carry no
/// <c>consume_source_item</c>, so the skill system leaves them in the bag and this effect takes
/// them. The piece goes out on the item detail packet, the way seating does, and the socketing
/// result packet closes the tab's run.
/// </para>
/// </remarks>
public class ItemSocketChange : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemSocketChange;

    /// <summary>The client tells the tab apart from a gem seating by this kind.</summary>
    private const byte KindSocketChange = 2;

    public override void Execute(BaseUnit caster,
        SkillCaster casterObj,
        BaseUnit target,
        SkillCastTarget targetObj,
        CastAction castObj,
        Skill skill,
        SkillObject skillObject,
        DateTime time,
        int value1,
        int value2,
        int value3,
        int value4)
    {
        Logger.Debug("Special effects: ItemSocketChange value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4);

        if (caster is not Character owner)
        {
            Logger.Error($"Special effects: ItemSocketChange caster {caster?.Id} is not a character");
            return;
        }

        if (casterObj is not SkillItem stoneSkillItem)
        {
            Logger.Error($"Special effects: ItemSocketChange casterObj {casterObj} is not a SkillItem");
            return;
        }

        if (targetObj is not SkillCastItemTarget skillTargetItem)
        {
            Logger.Error($"Special effects: ItemSocketChange targetObj {targetObj} is not a SkillCastItemTarget");
            return;
        }

        using var inventoryLease = owner.Inventory.AcquireMutation();
        skill.SkipAutomaticItemConsumption = true;
        var targetItem = owner.Inventory.GetItemById(skillTargetItem.Id);
        var stone = owner.Inventory.GetItemById(stoneSkillItem.ItemId);
        if (targetItem is null || stone is null)
        {
            Logger.Warn($"Special effects: ItemSocketChange target {skillTargetItem.Id} or stone {stoneSkillItem.ItemId} not found");
            return;
        }

        if (targetItem is not EquipItem equipItem ||
            !ReferenceEquals(stone._holdingContainer, owner.Inventory.Bag) ||
            stone.Template?.UseSkillId != skill.Template.Id ||
            stone.TemplateId != stoneSkillItem.ItemTemplateId ||
            !ItemSecurityPolicy.CanPerform(targetItem, ItemSecurityOperation.IrreversibleTransform) ||
            !ItemSecurityPolicy.CanPerform(stone, ItemSecurityOperation.DestroyOrConsume))
        {
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
            return;
        }

        if (!ItemManager.Instance.IsSocketChangeStone(stone.TemplateId))
        {
            Logger.Warn($"Special effects: ItemSocketChange item {stone.TemplateId} has no item_socket_changes rows");
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
            return;
        }

        // The sockets the tab ticked. A cast without the block, or with nothing ticked, is refused:
        // the tab never sends one, and guessing "all of them" would spend stones the player did not
        // put down.
        var mask = SelectedSockets(skillObject);
        if (mask == 0 || (mask >> EquipItem.NativeSocketCapacity) != 0)
        {
            Logger.Warn($"Special effects: ItemSocketChange from {owner.Name} carried no socket mask");
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
            return;
        }

        var changes = new List<(int index, uint from, uint to)>();
        for (var i = 0; i < EquipItem.NativeSocketCapacity; i++)
        {
            if ((mask & (1u << i)) == 0)
                continue;
            var seated = equipItem.NativeSocketItemIds.ElementAtOrDefault(i);
            if (seated == 0)
                continue;
            var becomes = ItemManager.Instance.GetSocketChangeTarget(stone.TemplateId, seated);
            if (becomes != 0)
                changes.Add((i, seated, becomes));
        }

        if (changes.Count == 0 || changes.Count != System.Numerics.BitOperations.PopCount(mask))
        {
            // A ticked socket holds nothing this stone changes. The tab greys those out itself, so
            // this is a stale window or a hand-built cast.
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
            return;
        }

        var labor = (long)value1 * changes.Count;
        if (value1 < 0 || labor > short.MaxValue || !owner.HasLaborPower((int)labor))
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughLaborPower);
            return;
        }
        if (stone.Count < changes.Count)
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughItem);
            return;
        }
        var tasks = new List<ItemTask>();
        var removed = new List<ulong>();
        if (!owner.TryCommitItemLabor((int)labor, 0, () =>
            owner.Inventory.Bag.TryConsumeExactItemsIntoTaskBatch([(stone, changes.Count)], tasks, removed)))
        {
            owner.SendErrorMessage(ErrorMessageType.NotEnoughItem);
            return;
        }
        foreach (var (index, _, to) in changes)
            equipItem.SetNativeSocket(index, to);
        tasks.Add(new ItemUpdate(equipItem));
        owner.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.ItemSocketChange, tasks, removed));

        equipItem.IsDirty = true;

        // The piece goes out on the detail packet, as seating does; the tab re-reads it from the bag.
        owner.SendPacket(new SCItemDetailUpdatedPacket(equipItem));
        if (equipItem.SlotType == SlotType.Equipment)
            owner.UpdateGearBonuses(null, null);

        // Close the tab's run. The type is the gem the first ticked socket became, since the client's
        // ITEM_SOCKET_UPGRADE notice names one gem.
        owner.SendPacket(new SCItemSocketingLunagemResultPacket(1, equipItem.Id, changes[0].to, KindSocketChange, true));

        Logger.Info("ItemSocketChange: {0} changed {1} socket(s) on item {2} with stone {3}: {4}",
            owner.Name, changes.Count, equipItem.Id, stone.TemplateId,
            string.Join(", ", changes.Select(c => $"[{c.index}] {c.from}->{c.to}")));

        // The normal skill lifecycle owns its single SkillEnded notification.
    }

    /// <summary>
    /// The socket bit mask the gear window sent with the cast, or 0 when the cast carried none.
    /// </summary>
    /// <remarks>
    /// The tab hands its tick state to <c>X2ItemEnchant:Execute(selectSlotBit)</c> and the client
    /// puts it, as is, in the first extra value. A cast with socket 1 ticked arrives as
    /// <c>values=[00000001]</c> (flag 12, one value). Bit N is socket N, and nine sockets is all the
    /// detail block has room for.
    /// </remarks>
    private static uint SelectedSockets(SkillObject skillObject)
    {
        if (skillObject is not SkillObjectExtraValues extras || extras.ReadCount == 0)
            return 0;

        return (uint)extras.Values[0] & ((1u << EquipItem.NativeSocketCapacity) - 1);
    }
}
