using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Units;

using ChangeMappingRoute = AAEmu.Game.Models.Game.Items.ItemChangeMapping;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Awakening (special effect 165). The scroll skill names a mapping group in value1, the equipment
/// arrives as the cast target, and skill object 26 optionally names the chosen route.
/// </summary>
public class ItemChangeMapping : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ItemChangeMapping;

    internal static bool IsFeatureEnabled(FeatureSet features) =>
        features is not null && features.Check(Feature.itemChangeMapping);

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

        if (!IsFeatureEnabled(FeaturesManager.Fsets) ||
            targetObj is not SkillCastItemTarget itemTarget)
        {
            Reject(character);
            return;
        }

        var group = ItemManager.Instance.GetChangeMappingGroup((uint)value1);
        var item = character.Inventory.GetItemById(itemTarget.Id);
        var mapping = ItemManager.Instance.GetChangeMapping(
            group, item, (skillObject as SkillObjectItemChangeMapping)?.MappingId ?? 0);
        if (group is null || item is null || mapping is null)
        {
            Logger.Warn("ItemChangeMapping: invalid group/item/grade for group {0}, target {1}",
                value1, itemTarget.Id);
            Reject(character, ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        if (!ItemSecurityPolicy.CanPerform(item, ItemSecurityOperation.IrreversibleTransform))
        {
            Reject(character, ErrorMessageType.ItemSecureCondition);
            return;
        }

        var targetTemplate = ItemManager.Instance.GetTemplate(mapping.TargetItemId);
        if (targetTemplate is null || targetTemplate.ClassType != item.Template.ClassType)
        {
            Logger.Warn("ItemChangeMapping: route {0} has incompatible or missing target template {1}",
                mapping.Id, mapping.TargetItemId);
            Reject(character);
            return;
        }

        var requirements = (skill?.Template?.Effects ?? [])
            .Where(effect => effect.ConsumeItemId != 0 && effect.ConsumeItemCount > 0)
            .Select(effect => (effect.ConsumeItemId, effect.ConsumeItemCount))
            .ToList();
        if (requirements.Count == 0)
        {
            Logger.Warn("ItemChangeMapping: skill {0} has no awakening reagent", skill?.Template?.Id);
            Reject(character);
            return;
        }

        var before = new PacketStream();
        item.Write(before);

        var equipItem = item as EquipItem;
        var snapshot = new ItemSnapshot(item, equipItem);
        var chance = ItemAwakeningCalculator.SuccessChance(group, equipItem?.MappingFailBonus ?? 0);
        var succeeded = ItemAwakeningCalculator.IsSuccess(
            chance, Random.Shared.Next(ItemAwakeningCalculator.ChanceScale));

        try
        {
            if (succeeded)
            {
                if (value3 < 0 || value3 > value4)
                    throw new InvalidOperationException(
                        $"Invalid awakening Temper loss range {value3}..{value4}");
                var temperLoss = value4 > 0
                    ? Random.Shared.Next(value3, value4 + 1)
                    : 0;
                Awaken(item, equipItem, mapping, group, targetTemplate);
                if (equipItem is not null)
                {
                    equipItem.ScaledA = ItemAwakeningCalculator.ResolveTemperAfterSuccess(
                        equipItem.ScaledA, value2, value3, value4, temperLoss);
                }
            }
            else if (equipItem is not null && group.FailBonus > 0)
            {
                var bonus = equipItem.MappingFailBonus + group.FailBonus / 100;
                equipItem.MappingFailBonus = (byte)Math.Min(bonus, byte.MaxValue);
            }
        }
        catch (Exception exception)
        {
            snapshot.Restore(item, equipItem);
            Logger.Error(exception, "ItemChangeMapping: failed to prepare route {0}", mapping.Id);
            Reject(character);
            return;
        }

        // This is the commit boundary. It preflights every required stack before taking the first
        // unit. If payment fails, restore the in-memory item before the client or persistence sees it.
        if (!character.Inventory.Bag.TryConsumeExactTemplates(ItemTaskType.GradeEnchant, requirements))
        {
            snapshot.Restore(item, equipItem);
            Logger.Warn("ItemChangeMapping: {0} could not atomically pay skill {1}",
                character.Name, skill?.Template?.Id);
            Reject(character, ErrorMessageType.NotEnoughRequiredItem);
            return;
        }

        // ApplyEffects queued the same consume_item rows before calling us. We own that payment now.
        skill.SkipAutomaticItemConsumption = true;
        item.IsDirty = true;

        if (item.SlotType == SlotType.Equipment)
            character.UpdateGearBonuses(null, null);

        // Re-state the full slot so the bag adopts the new template/detail, then close the request and
        // drive the retail Awakening Results dialog. Result 0 is success; any nonzero byte is failure.
        character.SendPacket(new SCItemTaskSuccessPacket(
            ItemTaskType.GradeEnchant, [new ItemAdd(item)], []));
        character.SendPacket(new SCItemChangeMappingResultPacket(
            before.GetBytes(), item, mapping.Id, (byte)(succeeded ? 0 : 1)));

        Logger.Info("ItemChangeMapping: {0} route {1}, item {2}->{3}, grade {4}, result {5}",
            character.Name, mapping.Id, snapshot.TemplateId, item.TemplateId, item.Grade,
            succeeded ? "success" : "failure");
    }

    private static void Awaken(Item item,
        EquipItem equipItem,
        ChangeMappingRoute mapping,
        ItemChangeMappingGroup group,
        ItemTemplate targetTemplate)
    {
        var sourceCategory = ItemManager.Instance.GetRndAttrCategoryForItem(item);
        var sourceAttributeGroups = equipItem?.RndAttrGroupIds.ToArray() ?? [];

        item.TemplateId = mapping.TargetItemId;
        item.Template = targetTemplate;
        var targetCategory = ItemManager.Instance.GetRndAttrCategoryForItem(item);

        if (equipItem is not null && group.EvolvingExpInherit &&
            sourceCategory is not null && targetCategory is not null)
        {
            var totalExp = ItemManager.Instance.GetEvolvingTotalExp(
                sourceCategory, item.Grade, equipItem.EvolvingExp);
            var startGrade = ItemManager.Instance.GetEvolvingLadderStartGrade(targetCategory);
            var (grade, remainingExp) = ItemManager.Instance.SpendEvolvingExp(
                targetCategory, startGrade, totalExp);
            item.Grade = grade;
            equipItem.EvolvingExp = remainingExp;
        }
        else if (mapping.TargetGradeId >= 0)
        {
            item.Grade = (byte)mapping.TargetGradeId;
            if (equipItem is not null)
                equipItem.EvolvingExp = 0;
        }
        else if (equipItem is not null && !group.EvolvingExpInherit)
        {
            equipItem.EvolvingExp = 0;
        }

        if (equipItem is null)
            return;

        var attributeResolution = ItemRandomAttributeResolver.ResolveForAwakening(
            sourceCategory,
            targetCategory,
            item.Grade,
            sourceAttributeGroups,
            maximum => Random.Shared.Next(maximum));
        if (!attributeResolution.IsValid)
            throw new InvalidOperationException(attributeResolution.FailureReason);

        equipItem.RndAttrGroupIds = attributeResolution.GroupIds;
        equipItem.MappingFailBonus = 0;

        Logger.Info("ItemChangeMapping: route {0} inherited effects [{1}] -> [{2}], added [{3}]",
            mapping.Id,
            string.Join(",", sourceAttributeGroups),
            string.Join(",", attributeResolution.GroupIds),
            string.Join(",", attributeResolution.AddedGroupIds));
    }

    private static void Reject(Character character, ErrorMessageType error = ErrorMessageType.Invalid)
    {
        character.SkillCancelled = true;
        if (error != ErrorMessageType.Invalid)
            character.SendErrorMessage(error);
    }

    private sealed class ItemSnapshot
    {
        public uint TemplateId { get; }
        private ItemTemplate Template { get; }
        private byte Grade { get; }
        private bool IsDirty { get; }
        private byte MappingFailBonus { get; }
        private ushort ScaledA { get; }
        private uint[] GemData { get; }

        public ItemSnapshot(Item item, EquipItem equipItem)
        {
            TemplateId = item.TemplateId;
            Template = item.Template;
            Grade = item.Grade;
            IsDirty = item.IsDirty;
            MappingFailBonus = equipItem?.MappingFailBonus ?? 0;
            ScaledA = equipItem?.ScaledA ?? 0;
            GemData = equipItem?.GemData?.ToArray();
        }

        public void Restore(Item item, EquipItem equipItem)
        {
            item.TemplateId = TemplateId;
            item.Template = Template;
            item.Grade = Grade;
            if (equipItem is not null)
            {
                equipItem.MappingFailBonus = MappingFailBonus;
                equipItem.ScaledA = ScaledA;
                equipItem.GemData = GemData?.ToArray();
            }
            item.IsDirty = IsDirty;
        }
    }
}
