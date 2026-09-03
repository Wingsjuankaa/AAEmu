using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>Random replacement of one synthesis effect (AA10 special effect 136).</summary>
public class ItemEvolvingReRoll : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemEvolvingReRoll;
    protected virtual bool RequiresExplicitGroup => false;

    internal static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.itemEvolvingReRoll);

    public override void Execute(
        BaseUnit caster,
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
        // The generic skill cleanup also sees the source stone. This effect owns the exact selected
        // stack, including every rejection path, so it must never be consumed a second time.
        if (skill is not null)
            skill.SkipAutomaticItemConsumption = true;

        if (caster is not Character owner ||
            targetObj is not SkillCastItemTarget itemTarget ||
            skillObject is not SkillObjectEvolvingRerollOptions options)
        {
            Reject(caster as Character, skill,
                $"The native r575 reroll context is incomplete " +
                $"(caster={casterObj?.GetType().Name ?? "null"}, target={targetObj?.GetType().Name ?? "null"}, " +
                $"options={skillObject?.GetType().Name ?? "null"}).");
            return;
        }

        if (!IsFeatureEnabled(FeaturesManager.Fsets))
        {
            Reject(owner, skill, "The itemEvolvingReRoll feature is disabled.");
            return;
        }

        if ((RequiresExplicitGroup && options.ChangeToGroupId == 0) ||
            (!RequiresExplicitGroup && options.ChangeToGroupId != 0))
        {
            Reject(owner, skill, RequiresExplicitGroup
                ? "Selectable reroll requires an explicit replacement group."
                : "Random reroll must not request an explicit replacement group.");
            return;
        }

        var targetItem = owner.Inventory.GetItemById(itemTarget.Id) as EquipItem;
        if (targetItem is null || !ReferenceEquals(targetItem._holdingContainer, owner.Inventory.Bag))
        {
            Reject(owner, skill, "The selected reroll target is stale or is not in the backpack.");
            return;
        }

        if (!ItemSecurityPolicy.CanPerform(targetItem, ItemSecurityOperation.IrreversibleTransform))
        {
            Reject(owner, skill, "The selected reroll target is secured.",
                ErrorMessageType.ItemSecureCondition);
            return;
        }

        var category = ItemManager.Instance.GetRndAttrCategoryForItem(targetItem);
        if (category is null)
        {
            Reject(owner, skill, $"Item {targetItem.TemplateId} has no synthesis-attribute category.");
            return;
        }

        Item reagent = null;
        var consumeChangeAttempt = false;
        switch (casterObj)
        {
            // When a Serendipity Stone is loaded, r575 casts from that exact item stack.
            case SkillItem reagentCaster:
            {
                reagent = owner.Inventory.GetItemById(reagentCaster.ItemId);
                if (reagent is null ||
                    !ReferenceEquals(reagent._holdingContainer, owner.Inventory.Bag) ||
                    reagent.Count < 1 ||
                    reagent.TemplateId != reagentCaster.ItemTemplateId ||
                    reagent.Template?.UseSkillId != skill?.Template?.Id)
                {
                    Reject(owner, skill, "The selected reroll stone is stale or invalid.",
                        ErrorMessageType.NotEnoughRequiredItem);
                    return;
                }

                var rerollSet = ItemManager.Instance.GetItemSet(category.ReRollItemSetId);
                var setEntry = rerollSet?.Items.Values.FirstOrDefault(entry => entry.ItemId == reagent.TemplateId);
                if (rerollSet is null || rerollSet.KindId != 3 ||
                    setEntry is null || setEntry.Count != 1 || reagent.Count < setEntry.Count)
                {
                    Reject(owner, skill,
                        $"Reagent {reagent.TemplateId} is not in category {category.Id}'s native reroll set.",
                        ErrorMessageType.NotEnoughRequiredItem);
                    return;
                }
                break;
            }

            // Native Hiram Change Attempts do not use a stone. The client casts skill 39836 from
            // the character (unit caster), targets the item, and sends only skill-object type 9.
            case SkillCasterUnit unitCaster when unitCaster.ObjId == owner.ObjId && !RequiresExplicitGroup:
                if (targetItem.EvolveChance == 0)
                {
                    Reject(owner, skill, "The target has no remaining Change Attempts.",
                        ErrorMessageType.NotEnoughRequiredItem);
                    return;
                }
                consumeChangeAttempt = true;
                break;

            default:
                Reject(owner, skill,
                    $"Unsupported r575 reroll caster {casterObj?.GetType().Name ?? "null"}.");
                return;
        }

        if (options.ModifierIndex > int.MaxValue)
        {
            Reject(owner, skill, $"Modifier index {options.ModifierIndex} is not representable.");
            return;
        }

        var resolution = ItemRandomAttributeResolver.ResolveReroll(
            category,
            targetItem.Grade,
            targetItem.RndAttrGroupIds,
            (int)options.ModifierIndex,
            options.ChangeToGroupId,
            maximum => Random.Shared.Next(maximum));
        if (!resolution.IsValid)
        {
            Reject(owner, skill, resolution.FailureReason);
            return;
        }

        if (resolution.ModifierIndex > byte.MaxValue ||
            resolution.Before.UnitAttributeId > ushort.MaxValue ||
            resolution.Before.UnitModifierTypeId > byte.MaxValue ||
            resolution.After.UnitAttributeId > ushort.MaxValue ||
            resolution.After.UnitModifierTypeId > byte.MaxValue)
        {
            Reject(owner, skill, "The resolved modifier cannot be represented by packet 0xCE.");
            return;
        }

        // All validation and RNG have completed. This is the commit boundary: if the exact stack has
        // changed since the request, nothing is consumed and the equipment remains untouched.
        if (reagent is not null &&
            !owner.Inventory.Bag.TryConsumeExactItems(ItemTaskType.GradeEnchant, [reagent]))
        {
            Reject(owner, skill, "The selected reroll stone changed before commit.",
                ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        if (consumeChangeAttempt)
        {
            // Recheck at the commit boundary in case another request spent the last attempt after
            // validation but before the attribute roll completed.
            if (targetItem.EvolveChance == 0)
            {
                Reject(owner, skill, "The target's last Change Attempt was already spent.",
                    ErrorMessageType.NotEnoughRequiredItem);
                return;
            }
            targetItem.EvolveChance--;
        }

        targetItem.RndAttrGroupIds = resolution.GroupIds;
        targetItem.IsDirty = true;
        if (targetItem.SlotType == SlotType.Equipment)
            owner.UpdateGearBonuses(null, null);

        // 0xCE animates and describes the replacement, while the detail packet carries the updated
        // persistent EvolveChance so reopening the window cannot resurrect a spent free attempt.
        owner.SendPacket(new SCItemDetailUpdatedPacket(targetItem));

        owner.SendPacket(new SCItemReRollEvolvingResultPacket(
            targetItem.Id,
            (byte)resolution.ModifierIndex,
            true,
            ToPacketModifier(resolution.Before, targetItem.Grade),
            ToPacketModifier(resolution.After, targetItem.Grade)));

        Logger.Info(
            "ItemEvolvingReRoll: character={0}, item={1}/{2}, index={3}, group={4}->{5}, requested={6}, " +
            "payment={7}, attempts={8}",
            owner.Name,
            targetItem.Id,
            targetItem.TemplateId,
            resolution.ModifierIndex,
            resolution.Before.Id,
            resolution.After.Id,
            options.ChangeToGroupId,
            reagent is null ? "change-attempt" : $"item:{reagent.TemplateId}",
            targetItem.EvolveChance);
    }

    private static SCItemReRollEvolvingResultPacket.EvolvingModifier ToPacketModifier(
        ItemRndAttrUnitModifierGroup group,
        byte grade) =>
        new((ushort)group.UnitAttributeId, (byte)group.UnitModifierTypeId, group.GetValue(grade));

    private static void Reject(
        Character owner,
        Skill skill,
        string reason,
        ErrorMessageType error = ErrorMessageType.Invalid)
    {
        if (skill is not null)
        {
            skill.SkipAutomaticItemConsumption = true;
            skill.Cancelled = true;
        }

        if (owner is not null && error != ErrorMessageType.Invalid)
            owner.SendErrorMessage(error);
        Logger.Warn("Rejected AA10 evolving reroll for character {0}: {1}", owner?.Id ?? 0, reason);
    }
}
