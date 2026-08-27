using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class SpawnPet : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.SpawnPet;

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
        if (skill is null || skill.Cancelled)
            return;

        if (caster is not Character owner || casterObj is not SkillItem skillData)
        {
            skill.Cancelled = true;
            Logger.Warn("SpawnPet rejected: caster contract is not Character/SkillItem");
            return;
        }

        var sourceItem = skillData.SkillSourceItem;
        var inventoryItem = owner.Inventory.GetItemById(skillData.ItemId);
        var failure = SummonMateBlockReason.MissingSourceItem;
        if (sourceItem is null || !ReferenceEquals(sourceItem, inventoryItem) ||
            !SummonMateContractService.Instance.TryResolve(
                sourceItem,
                skill.Id,
                owner.Id,
                out var contract,
                out failure))
        {
            skill.Cancelled = true;
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
            Logger.Warn(
                "SpawnPet rejected owner={0} item={1} tpl={2} skill={3} reason={4}",
                owner.Id,
                skillData.ItemId,
                sourceItem?.TemplateId ?? skillData.ItemTemplateId,
                skill.Id,
                sourceItem is null || !ReferenceEquals(sourceItem, inventoryItem)
                    ? SummonMateBlockReason.MissingSourceItem
                    : failure);
            return;
        }

        var result = owner.Mates.ToggleMate(skillData, contract);
        if (result == MateToggleResult.Rejected)
        {
            skill.Cancelled = true;
            owner.SendErrorMessage(ErrorMessageType.ItemCannotUse);
        }

        Logger.Debug(
            "SpawnPet owner={0} item={1} tpl={2} npc={3} skill={4} result={5}",
            owner.Id, sourceItem.Id, contract.ItemId, contract.NpcId, contract.SkillId, result);
    }
}
