using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Synthesis ("Item Growth" / 합성), special effect 123, carried by skill 30666 (아이템 합성하기).
/// </summary>
/// <remarks>
/// <para>
/// The caster item is an infusion (<c>impl_id 33 = EvolvingMaterial</c>, listed in
/// <c>item_evolving_materials</c>); the target is the piece of equipment being grown. Feeding the
/// infusion adds its category's <c>gain_exp</c> to the equipment's stored synthesis experience, and
/// each time that reaches the target category's <c>grade_exp</c> for the current grade the item
/// advances one grade order and the requirement is deducted.
/// </para>
/// <para>
/// Reaching a new grade preserves every existing Synthesis Effect and rolls only newly unlocked slots.
/// The number of promoted grades also grants the same number of free Change Attempts, capped at five.
/// </para>
/// </remarks>
public class ItemEvolving : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemEvolving;

    /// <summary>
    /// Whether synthesis is enabled. Checked at the entry point, before any validation, RNG, payment or
    /// item mutation. Fails closed: an absent feature set counts as disabled.
    /// </summary>
    internal static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.itemEvolving);

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
        if (caster is not Character character)
            return;

        if (!IsFeatureEnabled(FeaturesManager.Fsets))
            return;

        // Skill 30666 is target_type 9 (Item), so the equipment always arrives as the cast target.
        if (targetObj is not SkillCastItemTarget itemTarget)
        {
            Logger.Warn("ItemEvolving: unexpected target {0} (expected SkillCastItemTarget)",
                targetObj?.GetType().Name ?? "null");
            return;
        }

        var equipItem = character.Inventory.GetItemById(itemTarget.Id) as EquipItem;
        if (equipItem is null)
            return;

        var targetCategory = ItemManager.Instance.GetRndAttrCategoryForItem(equipItem);
        if (targetCategory is null)
        {
            character.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        // Full means the bar at this grade is already topped out - more EXP would be thrown away.
        if (targetCategory.IsFull(equipItem.Grade, equipItem.EvolvingExp))
        {
            character.SendErrorMessage(ErrorMessageType.GradeEnchantMax);
            return;
        }

        // The synthesis window has six material slots and sends them as skill object type 8. Older
        // item-on-item shapes (caster item, enchant-style support item) are still honored so the
        // effect works if anything else ever casts this skill.
        if (!TryResolveMaterials(character, targetCategory, equipItem.Id, casterObj, skillObject, out var materials))
        {
            character.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        long gainExpLong = 0;
        long bonusExpLong = 0;
        foreach (var (item, category) in materials)
        {
            var property = category.GetProperty(item.Grade);
            gainExpLong += property?.GainExp ?? 0;
            bonusExpLong += RollBonusExp(property);
        }

        if (gainExpLong <= 0 || gainExpLong + bonusExpLong > int.MaxValue)
        {
            character.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            return;
        }
        var gainExp = (int)gainExpLong;
        var bonusExp = (int)bonusExpLong;

        // Resolve the entire result before accepting payment. A malformed attribute closure must not
        // consume infusions and then discover that the item cannot be represented.
        var startingGrade = equipItem.Grade;
        var (newGrade, remainingExp) =
            ItemManager.Instance.SpendEvolvingExp(targetCategory, startingGrade,
                equipItem.EvolvingExp + gainExp + bonusExp);
        var attributeResolution = ItemRandomAttributeResolver.ResolveForSynthesis(
            targetCategory,
            newGrade,
            equipItem.RndAttrGroupIds,
            maximum => Random.Shared.Next(maximum));
        if (!attributeResolution.IsValid)
        {
            Logger.Error("ItemEvolving: cannot resolve attributes for item {0}: {1}",
                equipItem.Id, attributeResolution.FailureReason);
            character.SendErrorMessage(ErrorMessageType.Invalid);
            return;
        }

        var startingGradeTemplate = ItemManager.Instance.GetGradeTemplate(startingGrade);
        var newGradeTemplate = ItemManager.Instance.GetGradeTemplate(newGrade);
        var promotedGrades = startingGradeTemplate is null || newGradeTemplate is null
            ? 0
            : Math.Max(0, newGradeTemplate.GradeOrder - startingGradeTemplate.GradeOrder);
        var addChance = ItemSynthesisCalculator.CalculateAddedChangeAttempts(
            equipItem.EvolveChance, promotedGrades);

        var addedAttributes = new List<SCItemEvolvingResultPacket.EvolvingAttribute>();
        foreach (var groupId in attributeResolution.AddedGroupIds)
        {
            var group = ItemManager.Instance.GetRndAttrGroup(groupId);
            if (group is null || group.UnitAttributeId > ushort.MaxValue || group.UnitModifierTypeId > byte.MaxValue)
            {
                Logger.Error("ItemEvolving: group {0} cannot be represented in the r575 result packet", groupId);
                character.SendErrorMessage(ErrorMessageType.Invalid);
                return;
            }
            addedAttributes.Add(new SCItemEvolvingResultPacket.EvolvingAttribute(
                (ushort)group.UnitAttributeId,
                (byte)group.UnitModifierTypeId,
                group.GetValue(newGrade)));
        }

        // Charged in the category's own currency, and from AA points instead of coin when the request
        // asked for that. Checked, and performed before anything is destroyed, so a refused charge
        // cannot reach the materials. Every shipped category names currency 0 (gold), so the other
        // branches of TryPayCurrency are reachable only if that ever changes.
        var cost = EvolvingCost(targetCategory, equipItem, gainExp + bonusExp);
        var autoUseAaPoint = skillObject is SkillObjectItemEvolvingMaterials { AutoUseAaPoint: true };
        if (!character.TryPayCurrency(targetCategory.CurrencyId, cost, autoUseAaPoint, ItemTaskType.GradeEnchant))
            return;

        // The exact-item helper validates every selected stack before touching the first one and emits
        // one inventory task only after all list/count mutations have committed. A stale slot therefore
        // refunds the already accepted charge without losing an earlier infusion.
        if (!character.Inventory.Bag.TryConsumeExactItems(
                ItemTaskType.GradeEnchant,
                materials.Select(entry => entry.Item).ToList()))
        {
            Logger.Error("ItemEvolving: {0} could not atomically consume {1} selected materials",
                character.Name, materials.Count);
            RefundCost(character, targetCategory.CurrencyId, cost, autoUseAaPoint);
            character.SendErrorMessage(ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        Logger.Info("ItemEvolving: {0} consumed {1} material slots: {2}",
            character.Name,
            materials.Count,
            string.Join(",", materials.Select(entry => $"{entry.Item.Id}/{entry.Item.TemplateId}")));

        equipItem.Grade = newGrade;
        equipItem.EvolvingExp = remainingExp;
        equipItem.RndAttrGroupIds = attributeResolution.GroupIds;
        equipItem.EvolveChance = (ushort)(equipItem.EvolveChance + addChance);

        // UpdateGearBonuses only runs on equip/unequip, so an item synthesized while worn would keep
        // scoring at its old grade and old attributes until it was re-equipped or the character
        // relogged.
        if (equipItem.SlotType == SlotType.Equipment)
            character.UpdateGearBonuses(null, null);

        // The accumulated EXP rides in the item detail, which has its own packet - the UpdateDetail
        // item task carries a 128-byte blob this client does not parse.
        character.SendPacket(new SCItemDetailUpdatedPacket(equipItem));

        if (equipItem.Grade != startingGrade)
        {
            character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.GradeEnchant,
                [new ItemGradeChange(equipItem, equipItem.Grade)], []));
        }

        // The client applies the new grade from this packet itself and pops the result dialog as
        // "old -> new". Equal grades with no bonus EXP means it stays silent, which is what an
        // EXP-only step should do.
        character.SendPacket(new SCItemEvolvingResultPacket(
            equipItem,
            equipItem.Grade,
            startingGrade,
            gainExp,
            bonusExp,
            addChance,
            addedAttributes));

        Logger.Info(
            "ItemEvolving: {0} item {1} grade {2}->{3}, change attempts +{4}={5}, effects [{6}]",
            character.Name,
            equipItem.Id,
            startingGrade,
            newGrade,
            addChance,
            equipItem.EvolveChance,
            string.Join(",", attributeResolution.GroupIds));
    }

    /// <summary>
    /// The material's own synthesis category, but only when the target actually accepts it: the
    /// category groups must be related, and the material must be within <c>material_grade_limit</c>.
    /// Null when this pairing is not legal.
    /// </summary>
    /// <remarks>
    /// A material can name its category two ways. <c>item_evolving_materials</c> is the explicit list,
    /// but it only holds 82 rows - consumables like the story quest infusion, which have no equipment
    /// row to carry the id. Everything else declares it the same way the target does, in
    /// <c>item_weapons</c>/<c>item_armors</c>/<c>item_accessories.item_rnd_attr_category_id</c>: the
    /// Ipnir weapon infusion (48140) sits in <c>item_armors</c> pointing at category 673
    /// (<c>live.19.07.craft_material_weapon.ipnir</c>, group 25), which the Ipnir weapon group 21
    /// accepts. Consulting only the explicit list rejected every infusion in the Ipnir and Erenor
    /// lines, and with them the lower-tier gear those categories also allow as material.
    /// </remarks>
    private static ItemRndAttrCategory GetUsableMaterialCategory(ItemRndAttrCategory targetCategory, Item materialItem)
    {
        var material = ItemManager.Instance.GetEvolvingMaterial(materialItem.TemplateId);
        var materialCategory = ItemManager.Instance.GetRndAttrCategory(material?.CategoryId ?? 0)
                               ?? ItemManager.Instance.GetRndAttrCategoryForItem(materialItem);
        if (materialCategory is null || !ItemManager.Instance.CanUseAsEvolvingMaterial(targetCategory, materialCategory))
            return null;

        // material_grade_limit caps how high-graded a material the target will accept. 255 = no cap.
        if (targetCategory.MaterialGradeLimit is >= 0 and < 255 && materialItem.Grade > targetCategory.MaterialGradeLimit)
            return null;

        return materialCategory;
    }

    /// <summary>
    /// The infusions this cast is spending, each paired with the category that prices it. Empty when
    /// the client named nothing usable — synthesis is never guessed at, since it destroys materials.
    /// </summary>
    private static bool TryResolveMaterials(Character character,
        ItemRndAttrCategory targetCategory,
        ulong targetItemId,
        SkillCaster casterObj,
        SkillObject skillObject,
        out List<(Item Item, ItemRndAttrCategory Category)> resolved)
    {
        resolved = [];
        if (skillObject is SkillObjectItemEvolvingMaterials { HasValidWireShape: false } malformed)
        {
            Logger.Warn("ItemEvolving: {0} sent invalid material payload length {1}",
                character.Name, malformed.DeclaredByteLength);
            return false;
        }

        var itemIds = skillObject switch
        {
            SkillObjectItemEvolvingMaterials evolving => evolving.UsedMaterialItemIds,
            SkillObjectItemGradeEnchantingSupport support when support.SupportItemId != 0 => [support.SupportItemId],
            _ => casterObj is SkillItem skillItem && skillItem.ItemId != 0 ? [skillItem.ItemId] : []
        };

        var seen = new HashSet<ulong>();
        foreach (var itemId in itemIds)
        {
            // The same slot twice would consume one item and charge for two.
            if (!seen.Add(itemId))
                return false;

            // Gear of a related category is legal material, so the piece being grown now qualifies as
            // its own material. Feeding it to itself would destroy it and pay out for the privilege.
            if (itemId == targetItemId)
            {
                Logger.Warn("ItemEvolving: {0} offered the target item {1} as its own material", character.Name, itemId);
                return false;
            }

            var item = character.Inventory.GetItemById(itemId);
            var category = item is null ? null : GetUsableMaterialCategory(targetCategory, item);
            if (category is null)
            {
                Logger.Warn("ItemEvolving: {0} offered item {1} which is not a material for category {2}",
                    character.Name, itemId, targetCategory.Id);
                return false;
            }

            // Everything ConsumeItem needs to succeed is settled here, so that the consume phase cannot
            // fail partway with earlier materials already destroyed. It looks the item up by template in
            // one container and takes a unit from the stack, so the material has to be in that same
            // container - GetItemById also reaches the bank and worn equipment - and the stack has to
            // have a unit to give.
            if (!ReferenceEquals(item._holdingContainer, character.Inventory.Bag))
            {
                Logger.Warn("ItemEvolving: {0} offered item {1} from {2}, which is not the bag",
                    character.Name, itemId, item._holdingContainer?.ContainerType.ToString() ?? "no container");
                return false;
            }

            if (item.Count < 1)
            {
                Logger.Warn("ItemEvolving: {0} offered item {1}, whose stack is empty", character.Name, itemId);
                return false;
            }

            resolved.Add((item, category));
        }

        return resolved.Count is > 0 and <= SkillObjectItemEvolvingMaterials.MaterialSlots;
    }

    /// <summary>
    /// Returns a charge taken by <see cref="Character.TryPayCurrency"/>, for the failure path that has
    /// already been paid. Only the currencies synthesis can charge are handled; anything else is logged
    /// rather than silently swallowed, since the alternative is quietly keeping the player's money.
    /// </summary>
    private static void RefundCost(Character character, uint currencyId, long cost, bool autoUseAaPoint)
    {
        if (cost <= 0)
            return;

        var refunded = (ContentCurrencyType)currencyId switch
        {
            ContentCurrencyType.Gold or ContentCurrencyType.GoldWithAaPoint => autoUseAaPoint
                ? character.AddAAPoint(SlotType.Inventory, cost)
                : character.AddMoney(SlotType.Inventory, cost),
            ContentCurrencyType.AaPoint => character.AddAAPoint(SlotType.Inventory, cost),
            _ => false
        };

        if (!refunded)
            Logger.Error("ItemEvolving: could not refund {0} of currency {1} to {2}", cost, currencyId, character.Name);
    }

    private static int RollBonusExp(ItemRndAttrCategoryProperty materialProperty)
    {
        if (materialProperty is null || materialProperty.BonusExpChance <= 0)
            return 0;

        var min = Math.Clamp(Math.Min(materialProperty.BonusExpMin, materialProperty.BonusExpMax), 0, 1000);
        var max = Math.Clamp(Math.Max(materialProperty.BonusExpMin, materialProperty.BonusExpMax), min, 1000);
        return ItemSynthesisCalculator.CalculateBonusExperience(
            materialProperty.GainExp,
            materialProperty,
            Random.Shared.Next(0, 1000),
            Random.Shared.Next(min, max + 1));
    }

    /// <summary>
    /// Evaluates <c>item_evolving_cost</c> (formula 64):
    /// <c>max(item_evolving_value * tier(item_level, item_evolving_cost_mul), 0)</c>.
    /// </summary>
    /// <remarks>
    /// <c>item_evolving_cost_mul</c> is the target category's <c>gold_mul</c>. <c>item_evolving_value</c>
    /// is supplied by the caller in retail and is not present in any shipped table nor referenced by the
    /// client, so the experience actually purchased by this step is used for it - the quantity the price
    /// is buying. If a retail cost table ever surfaces, this is the one input to revisit.
    /// </remarks>
    private static int EvolvingCost(ItemRndAttrCategory category, EquipItem item, int evolvingValue)
    {
        var property = category.GetProperty(item.Grade);
        if (property is null)
            return 0;

        var formula = FormulaManager.Instance.GetFormula((uint)FormulaKind.ItemEvolvingCost);
        if (formula is null)
            return 0;

        var parameters = new Dictionary<string, double>
        {
            { "item_evolving_value", evolvingValue },
            { "item_level", item.Template.Level },
            { "item_evolving_cost_mul", property.GoldMul }
        };

        var cost = formula.Evaluate(parameters);
        if (double.IsNaN(cost) || cost <= 0)
            return 0;
        return cost > int.MaxValue ? int.MaxValue : (int)cost;
    }
}
