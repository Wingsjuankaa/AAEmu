using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

public class DoodadFuncLootItem : DoodadFuncTemplate
{
    internal const int NativeChancePrecision = 10_000;

    // doodad_funcs
    // ReSharper disable once UnusedAutoPropertyAccessor.Global
    public WorldInteractionType WorldInteractionId { get; set; }
    public uint ItemId { get; init; }
    public int CountMin { get; init; }
    public int CountMax { get; init; }
    public int Percent { get; init; }
    public int RemainTime { get; init; }
    public uint GroupId { get; init; }

    public override void Use(BaseUnit caster, Doodad owner, uint skillId, int nextPhase = 0)
    {
        if (caster is Character)
            Logger.Debug($"DoodadFuncLootItem: skillId {skillId}, nextPhase {nextPhase},  ItemId {ItemId}, CountMin {CountMin}, CountMax {CountMax},  Percent {Percent}, RemainTime {RemainTime}, GroupId {GroupId}");
        else
            Logger.Trace($"DoodadFuncLootItem: skillId {skillId}, nextPhase {nextPhase},  ItemId {ItemId}, CountMin {CountMin}, CountMax {CountMax},  Percent {Percent}, RemainTime {RemainTime}, GroupId {GroupId}");

        owner.ToNextPhase = false;
        if (caster is not Character character)
            return;

        var res = true;

        var chanceRoll = Random.Shared.Next(NativeChancePrecision);
        if (!IsSuccessfulRoll(Percent, chanceRoll))
            return;

        if (!TryGetInclusiveCount(Random.Shared, CountMin, CountMax, out var count))
            return;

        if (ItemId == 500)
        {
            character.Money += count;
            res = character.AddMoney(SlotType.Inventory, count);
        }
        else
        {
            if (ItemManager.Instance.IsAutoEquipTradePack(ItemId))
            {
                var item = ItemManager.Instance.Create(ItemId, count, 0);
                if (character.Inventory.TakeoffBackpack(ItemTaskType.RecoverDoodadItem, true))
                {
                    res = character.Inventory.Equipment.AddOrMoveExistingItem(ItemTaskType.RecoverDoodadItem, item,
                        (int)EquipmentItemSlot.Backpack);
                }
            }
            else
            {
                res = character.Inventory.Bag.AcquireDefaultItem(ItemTaskType.RecoverDoodadItem, ItemId, count);
            }
        }

        if (res == false)
            character.SendErrorMessage(ErrorMessageType.BagInvalidItem);

        // Move to next phase only when loot was actually granted.
        owner.ToNextPhase = res;
    }

    internal static bool IsSuccessfulRoll(int percent, int roll)
    {
        if (percent <= 0 || roll < 0 || roll >= NativeChancePrecision)
            return false;

        return roll < Math.Min(percent, NativeChancePrecision);
    }

    internal static bool TryGetInclusiveCount(Random random, int countMin, int countMax, out int count)
    {
        count = 0;
        if (random == null || countMax < countMin)
            return false;

        count = checked((int)random.NextInt64(countMin, (long)countMax + 1));
        return true;
    }
}
