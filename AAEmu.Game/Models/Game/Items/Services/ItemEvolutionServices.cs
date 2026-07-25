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
    }

    public sealed class ItemRandomAttributeService : IItemRandomAttributeService
    {
        public static ItemRandomAttributeService Instance { get; } = new();

        public IReadOnlyList<ItemRndAttrUnitModifierGroupSet> GetAvailableGroupSets(
            EquipItem target)
        {
            return target == null
                ? new List<ItemRndAttrUnitModifierGroupSet>()
                : ItemEvolutionRuleService.Instance
                    .GetProfile(target.TemplateId, target.Grade)
                    .ModifierGroupSets;
        }
    }
}
