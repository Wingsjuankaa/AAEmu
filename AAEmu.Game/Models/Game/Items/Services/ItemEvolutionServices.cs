using System;
using System.Collections.Generic;
using System.Linq;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public enum ItemEvolutionValidationFailure
    {
        None = 0,
        CatalogueUnavailable,
        TargetNotEquipment,
        TargetDefinitionMissing,
        TargetAtMaximumGrade,
        MaterialMissing,
        MaterialDefinitionMissing,
        MaterialNotAllowed,
        MaterialGradeTooHigh,
        InvalidMaterialCount,
        ExperienceOverflow,
        CostOverflow
    }

    public sealed class ItemEvolutionState
    {
        public uint ItemTemplateId { get; set; }
        public int GradeId { get; set; }
        public uint SectionExperience { get; set; }
        public ushort EvolutionChance { get; set; }
        public byte MappingFailBonus { get; set; }
        public IReadOnlyList<uint> RandomModifierIds { get; set; } =
            new List<uint>();
    }

    public interface IItemEvolutionStateService
    {
        ItemEvolutionState Read(EquipItem item);
        void WriteSynthesisState(
            EquipItem item,
            int gradeId,
            uint sectionExperience);
        void WriteRandomModifierIds(
            EquipItem item,
            IReadOnlyList<uint> modifierIds);
        void CopyForAwakening(
            EquipItem source,
            EquipItem target,
            bool inheritExperience);
    }

    public sealed class ItemEvolutionStateService : IItemEvolutionStateService
    {
        public static ItemEvolutionStateService Instance { get; } = new();

        public ItemEvolutionState Read(EquipItem item)
        {
            if (item == null)
                return null;

            var modifierIds = new List<uint>(
                EquipItem.NativeRandomModifierCapacity);
            for (var index = 0;
                 index < EquipItem.NativeRandomModifierCapacity;
                 index++)
                modifierIds.Add(item.GetNativeRandomModifierId(index));

            return new ItemEvolutionState
            {
                ItemTemplateId = item.TemplateId,
                GradeId = item.Grade,
                SectionExperience = item.EvolutionExperience,
                EvolutionChance = item.EvolveChance,
                MappingFailBonus = item.MappingFailBonus,
                RandomModifierIds = modifierIds
            };
        }

        public void WriteSynthesisState(
            EquipItem item,
            int gradeId,
            uint sectionExperience)
        {
            if (item == null)
                throw new ArgumentNullException(nameof(item));
            if (gradeId < byte.MinValue || gradeId > byte.MaxValue)
                throw new ArgumentOutOfRangeException(nameof(gradeId));

            item.Grade = (byte)gradeId;
            item.EvolutionExperience = sectionExperience;
            item.IsDirty = true;
        }

        public void WriteRandomModifierIds(
            EquipItem item,
            IReadOnlyList<uint> modifierIds)
        {
            if (item == null)
                throw new ArgumentNullException(nameof(item));
            if (modifierIds == null ||
                modifierIds.Count > EquipItem.NativeRandomModifierCapacity)
                throw new ArgumentOutOfRangeException(nameof(modifierIds));

            for (var index = 0;
                 index < EquipItem.NativeRandomModifierCapacity;
                 index++)
            {
                item.SetNativeRandomModifierId(
                    index,
                    index < modifierIds.Count ? modifierIds[index] : 0);
            }
            item.IsDirty = true;
        }

        public void CopyForAwakening(
            EquipItem source,
            EquipItem target,
            bool inheritExperience)
        {
            if (source == null)
                throw new ArgumentNullException(nameof(source));
            if (target == null)
                throw new ArgumentNullException(nameof(target));

            target.EvolutionExperience =
                inheritExperience ? source.EvolutionExperience : 0;
            target.EvolveChance = source.EvolveChance;
            target.MappingFailBonus = 0;
            for (var index = 0;
                 index < EquipItem.NativeRandomModifierCapacity;
                 index++)
            {
                target.SetNativeRandomModifierId(
                    index,
                    source.GetNativeRandomModifierId(index));
            }
            target.IsDirty = true;
        }
    }

    public sealed class SynthesisMaterialSelection
    {
        public Item Item { get; set; }
        public int Count { get; set; }
    }

    public sealed class SynthesisPreview
    {
        public ItemEvolutionValidationFailure Failure { get; set; }
        public string FailureReason { get; set; } = string.Empty;
        public EquipItem Target { get; set; }
        public IReadOnlyList<SynthesisMaterialSelection> Materials { get; set; } =
            new List<SynthesisMaterialSelection>();
        public int BeforeGradeId { get; set; }
        public uint BeforeSectionExperience { get; set; }
        public long MaterialExperience { get; set; }
        public int AfterGradeId { get; set; }
        public uint AfterSectionExperience { get; set; }
        public long GoldCost { get; set; }
        public int LaborCost { get; set; }
        public int BonusExperienceChance { get; set; }
        public int BonusExperienceMinimum { get; set; }
        public int BonusExperienceMaximum { get; set; }
        public int MaximumRandomModifierCount { get; set; }
        public bool IsValid => Failure == ItemEvolutionValidationFailure.None;
    }

    public sealed class SynthesisTransactionPlan
    {
        public SynthesisPreview Preview { get; set; }
        public long ResolvedExperience { get; set; }
        public long BonusExperience { get; set; }
        public int AfterGradeId { get; set; }
        public uint AfterSectionExperience { get; set; }
    }

    public sealed class SynthesisResult
    {
        public bool Success { get; set; }
        public long AppliedExperience { get; set; }
        public long BonusExperience { get; set; }
        public int BeforeGradeId { get; set; }
        public int AfterGradeId { get; set; }
        public uint AfterSectionExperience { get; set; }
    }

    public interface IItemSynthesisService
    {
        SynthesisPreview CreatePreview(
            EquipItem target,
            IReadOnlyList<SynthesisMaterialSelection> materials,
            int laborCost);
        bool TryResolveGrades(
            EquipItem target,
            long addedExperience,
            out int gradeId,
            out uint sectionExperience);
        SynthesisTransactionPlan CreateTransactionPlan(
            SynthesisPreview preview,
            int chanceRoll,
            int bonusPermilleRoll,
            bool forceBonusExperience);
    }

    /// <summary>
    /// Native AA8 synthesis preview authority. Formula provenance:
    /// x2game mode-7 vtable slots 36/38/39. Material gain is the selected
    /// material grade property's gain_exp. Gold is
    /// floor(target.gold_mul * materialExp * 0.001). Grade progression
    /// repeatedly consumes target grade_exp from detail +0x40.
    /// </summary>
    public sealed class ItemSynthesisService : IItemSynthesisService
    {
        private readonly IItemEvolutionRuleService _rules;

        public static ItemSynthesisService Instance { get; } =
            new(ItemEvolutionRuleService.Instance);

        public ItemSynthesisService(IItemEvolutionRuleService rules)
        {
            _rules = rules ?? throw new ArgumentNullException(nameof(rules));
        }

        public SynthesisPreview CreatePreview(
            EquipItem target,
            IReadOnlyList<SynthesisMaterialSelection> materials,
            int laborCost)
        {
            var preview = new SynthesisPreview
            {
                Target = target,
                Materials = materials ?? new List<SynthesisMaterialSelection>(),
                BeforeGradeId = target?.Grade ?? 0,
                BeforeSectionExperience = target?.EvolutionExperience ?? 0,
                LaborCost = Math.Max(0, laborCost)
            };
            var rules = _rules;
            if (!rules.NativeCatalogueAvailable)
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.CatalogueUnavailable,
                    "The native AA8 evolution catalogue is not loaded.");
            if (target == null)
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.TargetNotEquipment,
                    "The synthesis target is not equipment.");

            var targetProfile = rules.GetProfile(target.TemplateId, target.Grade);
            if (!targetProfile.HasSynthesisDefinition ||
                targetProfile.Property == null)
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.TargetDefinitionMissing,
                    "The target has no complete native AA8 synthesis definition.");
            if (target.Grade >= targetProfile.Category.MaxEvolvingGrade)
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.TargetAtMaximumGrade,
                    "The target is already at its native synthesis grade limit.");
            if (materials == null || materials.Count == 0)
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.MaterialMissing,
                    "No synthesis material was selected.");

            long materialExperience = 0;
            foreach (var selection in materials)
            {
                if (selection?.Item == null)
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.MaterialMissing,
                        "A selected synthesis material no longer exists.");
                if (selection.Count < 1 || selection.Count > selection.Item.Count)
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.InvalidMaterialCount,
                        "A selected synthesis material count is invalid.");
                if (!targetProfile.ValidMaterialItemIds.Contains(
                        selection.Item.TemplateId))
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.MaterialNotAllowed,
                        $"Item {selection.Item.TemplateId} is not related to " +
                        $"native AA8 target group {targetProfile.Category.CategoryGroupId}.");
                if (targetProfile.Category.MaterialGradeLimit >= 0 &&
                    selection.Item.Grade >
                    targetProfile.Category.MaterialGradeLimit)
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.MaterialGradeTooHigh,
                        $"Material grade {selection.Item.Grade} exceeds the " +
                        $"native limit {targetProfile.Category.MaterialGradeLimit}.");

                var materialProfile = rules.GetProfile(
                    selection.Item.TemplateId,
                    selection.Item.Grade);
                if (!materialProfile.IsSynthesisMaterial ||
                    materialProfile.Property == null ||
                    materialProfile.Property.GainExp <= 0)
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.MaterialDefinitionMissing,
                        $"Material {selection.Item.TemplateId} grade " +
                        $"{selection.Item.Grade} has no native gain_exp row.");

                try
                {
                    materialExperience = checked(
                        materialExperience +
                        (long)materialProfile.Property.GainExp * selection.Count);
                }
                catch (OverflowException)
                {
                    return Fail(
                        preview,
                        ItemEvolutionValidationFailure.ExperienceOverflow,
                        "The selected material experience overflows the supported range.");
                }
            }

            preview.MaterialExperience = materialExperience;
            try
            {
                // DAT_39cb864c = 0.001000000047, confirmed directly from
                // x2game. Integer truncation matches mode-7 slot 39.
                preview.GoldCost = checked(
                    (long)Math.Truncate(
                        targetProfile.Property.GoldMultiplier *
                        materialExperience *
                        0.0010000000474974513d));
            }
            catch (OverflowException)
            {
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.CostOverflow,
                    "The native AA8 synthesis currency cost overflows.");
            }

            if (!TryResolveGrades(
                    target,
                    materialExperience,
                    out var afterGrade,
                    out var afterExperience))
                return Fail(
                    preview,
                    ItemEvolutionValidationFailure.ExperienceOverflow,
                    "The native AA8 grade progression could not be resolved.");

            preview.AfterGradeId = afterGrade;
            preview.AfterSectionExperience = afterExperience;
            preview.BonusExperienceChance =
                targetProfile.Property.BonusExpChance;
            preview.BonusExperienceMinimum =
                targetProfile.Property.BonusExpMin;
            preview.BonusExperienceMaximum =
                targetProfile.Property.BonusExpMax;
            preview.MaximumRandomModifierCount =
                rules.GetProfile(target.TemplateId, afterGrade)
                    .Property?.MaxUnitModifierNum ?? 0;
            return preview;
        }

        public bool TryResolveGrades(
            EquipItem target,
            long addedExperience,
            out int gradeId,
            out uint sectionExperience)
        {
            gradeId = target?.Grade ?? 0;
            sectionExperience = target?.EvolutionExperience ?? 0;
            if (target == null || addedExperience < 0)
                return false;

            var rules = _rules;
            var profile = rules.GetProfile(target.TemplateId, gradeId);
            if (!profile.HasSynthesisDefinition || profile.Category == null)
                return false;

            long current;
            try
            {
                current = checked((long)sectionExperience + addedExperience);
            }
            catch (OverflowException)
            {
                return false;
            }

            while (gradeId < profile.Category.MaxEvolvingGrade)
            {
                var gradeProfile = rules.GetProfile(target.TemplateId, gradeId);
                var required = gradeProfile.Property?.GradeExp ?? 0;
                if (required <= 0 || current < required)
                    break;
                current -= required;
                gradeId++;
            }

            if (current < 0 || current > uint.MaxValue)
                return false;
            sectionExperience = (uint)current;
            return true;
        }

        public SynthesisTransactionPlan CreateTransactionPlan(
            SynthesisPreview preview,
            int chanceRoll,
            int bonusPermilleRoll,
            bool forceBonusExperience)
        {
            if (preview == null)
                throw new ArgumentNullException(nameof(preview));
            if (!preview.IsValid)
                throw new InvalidOperationException(
                    "An invalid synthesis preview cannot be resolved.");
            if (chanceRoll < 0 || chanceRoll >= 1000)
                throw new ArgumentOutOfRangeException(nameof(chanceRoll));

            // Native AA8 category properties use permille for probability and
            // bonus ranges. The catalogue spans 0..990 for chance and
            // 0..1000 for bonus, while the client renders result percentages
            // with a 1000.0 base (FUN_39301ec0).
            var bonusMinimum = Math.Clamp(
                preview.BonusExperienceMinimum,
                0,
                1000);
            var bonusMaximum = Math.Clamp(
                preview.BonusExperienceMaximum,
                bonusMinimum,
                1000);
            if (bonusPermilleRoll < bonusMinimum ||
                bonusPermilleRoll > bonusMaximum)
                throw new ArgumentOutOfRangeException(
                    nameof(bonusPermilleRoll));

            var bonusTriggered =
                forceBonusExperience ||
                chanceRoll < Math.Clamp(
                    preview.BonusExperienceChance,
                    0,
                    1000);
            long bonusExperience = 0;
            if (bonusTriggered && bonusMaximum > 0)
            {
                bonusExperience = checked(
                    preview.MaterialExperience * bonusPermilleRoll / 1000);
            }

            var resolvedExperience = checked(
                preview.MaterialExperience + bonusExperience);
            if (!TryResolveGrades(
                    preview.Target,
                    resolvedExperience,
                    out var afterGradeId,
                    out var afterSectionExperience))
                throw new InvalidOperationException(
                    "The resolved synthesis experience is outside the native " +
                    "AA8 grade graph.");

            return new SynthesisTransactionPlan
            {
                Preview = preview,
                ResolvedExperience = resolvedExperience,
                BonusExperience = bonusExperience,
                AfterGradeId = afterGradeId,
                AfterSectionExperience = afterSectionExperience
            };
        }

        private static SynthesisPreview Fail(
            SynthesisPreview preview,
            ItemEvolutionValidationFailure failure,
            string reason)
        {
            preview.Failure = failure;
            preview.FailureReason = reason;
            return preview;
        }
    }

    public sealed class AwakeningPreview
    {
        public EquipItem Target { get; set; }
        public ItemChangeMapping Mapping { get; set; }
        public ItemChangeMappingGroup MappingGroup { get; set; }
        public IReadOnlyList<ItemAwakeningReactive> Reactives { get; set; } =
            new List<ItemAwakeningReactive>();
        public bool IsValid => Target != null && Mapping != null && MappingGroup != null;
    }

    public sealed class AwakeningTransactionPlan
    {
        public AwakeningPreview Preview { get; set; }
        public bool Success { get; set; }
        public bool Crystallized { get; set; }
    }

    public sealed class AwakeningResult
    {
        public bool Success { get; set; }
        public bool Crystallized { get; set; }
        public uint BeforeTemplateId { get; set; }
        public uint AfterTemplateId { get; set; }
    }

    public interface IItemAwakeningService
    {
        IReadOnlyList<AwakeningPreview> GetAvailableMappings(EquipItem target);
    }

    public sealed class ItemAwakeningService : IItemAwakeningService
    {
        public static ItemAwakeningService Instance { get; } = new();

        public IReadOnlyList<AwakeningPreview> GetAvailableMappings(EquipItem target)
        {
            if (target == null)
                return new List<AwakeningPreview>();
            var rules = ItemEvolutionRuleService.Instance;
            return rules.GetProfile(target.TemplateId, target.Grade)
                .AwakeningMappings
                .Select(mapping => new AwakeningPreview
                {
                    Target = target,
                    Mapping = mapping,
                    MappingGroup = rules.GetMappingGroup(mapping.MappingGroupId),
                    Reactives = rules.GetAwakeningReactives(
                        mapping.MappingGroupId)
                })
                .Where(preview => preview.MappingGroup != null)
                .ToList();
        }
    }

    public interface IItemRandomAttributeService
    {
        IReadOnlyList<ItemRndAttrUnitModifierGroupSet> GetAvailableGroupSets(
            EquipItem target);
        ItemRandomAttributeResolution ResolveForSynthesis(
            EquipItem target,
            int afterGradeId,
            uint afterSectionExperience,
            Func<int, int> nextRandom);
        IReadOnlyList<ItemRandomAttributeValue> GetCurrentValues(EquipItem target);
    }

    public sealed class ItemRandomAttributeValue
    {
        public uint ModifierId { get; set; }
        public uint GroupId { get; set; }
        public ushort UnitAttributeId { get; set; }
        public byte UnitModifierTypeId { get; set; }
        public int Value { get; set; }
        public bool Added { get; set; }
    }

    public sealed class ItemRandomAttributeResolution
    {
        public bool IsValid { get; set; }
        public string FailureReason { get; set; } = string.Empty;
        public IReadOnlyList<uint> ModifierIds { get; set; } = new List<uint>();
        public IReadOnlyList<ItemRandomAttributeValue> Values { get; set; } =
            new List<ItemRandomAttributeValue>();
    }

    public sealed class ItemRandomAttributeService : IItemRandomAttributeService
    {
        public static ItemRandomAttributeService Instance { get; } = new();

        private readonly IItemEvolutionRuleService _rules;

        public ItemRandomAttributeService()
            : this(ItemEvolutionRuleService.Instance)
        {
        }

        public ItemRandomAttributeService(IItemEvolutionRuleService rules)
        {
            _rules = rules ?? throw new ArgumentNullException(nameof(rules));
        }

        public IReadOnlyList<ItemRndAttrUnitModifierGroupSet> GetAvailableGroupSets(
            EquipItem target)
        {
            return target == null
                ? new List<ItemRndAttrUnitModifierGroupSet>()
                : _rules
                    .GetProfile(target.TemplateId, target.Grade)
                    .ModifierGroupSets;
        }

        public ItemRandomAttributeResolution ResolveForSynthesis(
            EquipItem target,
            int afterGradeId,
            uint afterSectionExperience,
            Func<int, int> nextRandom)
        {
            if (target == null)
                return FailAttributes("The synthesis target is missing.");
            if (nextRandom == null)
                throw new ArgumentNullException(nameof(nextRandom));

            var profile = _rules.GetProfile(target.TemplateId, afterGradeId);
            var property = profile.Property;
            if (!profile.HasSynthesisDefinition || property == null)
                return FailAttributes(
                    "The target grade has no native AA8 random-attribute property.");

            var maximum = Math.Clamp(
                property.MaxUnitModifierNum,
                0,
                EquipItem.NativeRandomModifierCapacity);
            var selectedGroups = new List<ItemRndAttrUnitModifierGroup>();
            var existingGroupIds = new HashSet<uint>();
            var usedAttributes = new HashSet<uint>();

            for (var index = 0;
                 index < EquipItem.NativeRandomModifierCapacity;
                 index++)
            {
                var modifierId = target.GetNativeRandomModifierId(index);
                if (modifierId == 0)
                    continue;
                var modifier = _rules.GetModifierById(modifierId);
                var group = modifier == null
                    ? null
                    : _rules.GetModifierGroup(modifier.GroupId);
                if (modifier == null || group == null)
                    return FailAttributes(
                        $"Native AA8 modifier row {modifierId} is missing.");
                if (!existingGroupIds.Add(group.Id) ||
                    !usedAttributes.Add(group.UnitAttributeId))
                    return FailAttributes(
                        $"Native AA8 modifier row {modifierId} duplicates an " +
                        "existing group or attribute.");
                selectedGroups.Add(group);
            }

            if (selectedGroups.Count > maximum)
                return FailAttributes(
                    "The item contains more random attributes than its native " +
                    "AA8 grade permits.");

            var addedGroupIds = new HashSet<uint>();
            foreach (var groupSet in profile.ModifierGroupSets
                         .OrderBy(value => value.Id))
            {
                if (selectedGroups.Count >= maximum)
                    break;

                var selectedInSet = selectedGroups.Count(
                    group => group.GroupSetId == groupSet.Id);
                var quota = Math.Min(
                    Math.Max(groupSet.PickCount - selectedInSet, 0),
                    maximum - selectedGroups.Count);
                for (var pick = 0; pick < quota; pick++)
                {
                    var candidates = _rules.GetModifierGroups(groupSet.Id)
                        .Where(group =>
                            !existingGroupIds.Contains(group.Id) &&
                            !usedAttributes.Contains(group.UnitAttributeId) &&
                            _rules.GetModifier(group.Id, afterGradeId) != null)
                        .ToList();
                    if (candidates.Count == 0)
                        return FailAttributes(
                            $"Native AA8 modifier set {groupSet.Id} cannot " +
                            $"satisfy pick_count={groupSet.PickCount}.");

                    var fixedCandidates = candidates
                        .Where(group => group.FixedAttribute)
                        .ToList();
                    var selected = SelectWeighted(
                        fixedCandidates.Count > 0
                            ? fixedCandidates
                            : candidates,
                        nextRandom);
                    selectedGroups.Add(selected);
                    existingGroupIds.Add(selected.Id);
                    usedAttributes.Add(selected.UnitAttributeId);
                    addedGroupIds.Add(selected.Id);
                }
            }

            if (selectedGroups.Count != maximum)
                return FailAttributes(
                    $"Native AA8 requires {maximum} attributes at grade " +
                    $"{afterGradeId}, but only {selectedGroups.Count} could be resolved.");

            var values = new List<ItemRandomAttributeValue>(selectedGroups.Count);
            var ids = new List<uint>(selectedGroups.Count);
            foreach (var group in selectedGroups)
            {
                var modifier = _rules.GetModifier(group.Id, afterGradeId);
                if (modifier == null)
                    return FailAttributes(
                        $"Native AA8 modifier group {group.Id} has no row for " +
                        $"grade {afterGradeId}.");
                ids.Add(modifier.Id);
                values.Add(CreateValue(
                    group,
                    modifier,
                    property,
                    afterSectionExperience,
                    addedGroupIds.Contains(group.Id)));
            }

            return new ItemRandomAttributeResolution
            {
                IsValid = true,
                ModifierIds = ids,
                Values = values
            };
        }

        public IReadOnlyList<ItemRandomAttributeValue> GetCurrentValues(
            EquipItem target)
        {
            if (target == null)
                return new List<ItemRandomAttributeValue>();
            var property = _rules.GetProfile(target.TemplateId, target.Grade).Property;
            if (property == null)
                return new List<ItemRandomAttributeValue>();

            var values = new List<ItemRandomAttributeValue>();
            for (var index = 0;
                 index < EquipItem.NativeRandomModifierCapacity;
                 index++)
            {
                var modifier = _rules.GetModifierById(
                    target.GetNativeRandomModifierId(index));
                var group = modifier == null
                    ? null
                    : _rules.GetModifierGroup(modifier.GroupId);
                if (modifier == null || group == null)
                    continue;
                values.Add(CreateValue(
                    group,
                    modifier,
                    property,
                    target.EvolutionExperience,
                    false));
            }
            return values;
        }

        private static ItemRndAttrUnitModifierGroup SelectWeighted(
            IReadOnlyList<ItemRndAttrUnitModifierGroup> candidates,
            Func<int, int> nextRandom)
        {
            var totalWeight = candidates.Sum(value => Math.Max(value.Weight, 0));
            if (totalWeight <= 0)
                throw new InvalidOperationException(
                    "Native AA8 random-attribute candidates have no positive weight.");
            var roll = nextRandom(totalWeight);
            if (roll < 0 || roll >= totalWeight)
                throw new InvalidOperationException(
                    "The random-attribute roll is outside its native weight range.");
            foreach (var candidate in candidates)
            {
                roll -= Math.Max(candidate.Weight, 0);
                if (roll < 0)
                    return candidate;
            }
            throw new InvalidOperationException(
                "The native AA8 weighted random-attribute selection failed.");
        }

        private static ItemRandomAttributeValue CreateValue(
            ItemRndAttrUnitModifierGroup group,
            ItemRndAttrUnitModifier modifier,
            ItemRndAttrCategoryProperty property,
            uint sectionExperience,
            bool added)
        {
            // x2game FUN_39a4be10 and FUN_39a4be30:
            // progress = sectionExp / gradeExp;
            // value = minimum + (maximum - minimum) * progress.
            var progress = property.GradeExp > 0
                ? Math.Clamp(
                    (float)sectionExperience / property.GradeExp,
                    0f,
                    1f)
                : 0f;
            var value = (int)(
                (modifier.Maximum - modifier.Minimum) * progress +
                modifier.Minimum);
            return new ItemRandomAttributeValue
            {
                ModifierId = modifier.Id,
                GroupId = group.Id,
                UnitAttributeId = checked((ushort)group.UnitAttributeId),
                UnitModifierTypeId = checked((byte)group.UnitModifierTypeId),
                Value = value,
                Added = added
            };
        }

        private static ItemRandomAttributeResolution FailAttributes(string reason)
        {
            return new ItemRandomAttributeResolution
            {
                IsValid = false,
                FailureReason = reason
            };
        }
    }
}
