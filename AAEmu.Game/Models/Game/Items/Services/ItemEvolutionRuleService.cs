using System.Collections.Generic;
using System.Linq;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class ItemRndAttrCategory
    {
        public uint Id { get; set; }
        public uint CurrencyId { get; set; }
        public uint CategoryGroupId { get; set; }
        public int MaterialGradeLimit { get; set; }
        public int MaxEvolvingGrade { get; set; }
        public int MessageGrade { get; set; }
        public uint ReRollItemSetId { get; set; }
    }

    public sealed class ItemRndAttrCategoryGroup
    {
        public uint Id { get; set; }
        public string Name { get; set; } = string.Empty;
    }

    public sealed class ItemRndAttrCategoryRelation
    {
        public uint Id { get; set; }
        public uint CategoryGroupId { get; set; }
        public uint MaterialItemId { get; set; }
    }

    public sealed class ItemRndAttrCategoryProperty
    {
        public uint Id { get; set; }
        public int BonusExpChance { get; set; }
        public int BonusExpMax { get; set; }
        public int BonusExpMin { get; set; }
        public int GainExp { get; set; }
        public int GoldMultiplier { get; set; }
        public int GradeId { get; set; }
        public int GradeExp { get; set; }
        public uint CategoryId { get; set; }
        public int MaxElementLevel { get; set; }
        public int MaxUnitModifierNum { get; set; }
    }

    public sealed class ItemRndAttrCategoryElement
    {
        public uint Id { get; set; }
        public int ConsumeLabor { get; set; }
        public uint CategoryId { get; set; }
        public int Level { get; set; }
        public int RequiredExp { get; set; }
        public int Tax { get; set; }
    }

    public sealed class ItemEvolvingMaterial
    {
        public uint ItemId { get; set; }
        public uint CategoryId { get; set; }
        public bool ShowExp { get; set; }
    }

    public sealed class ItemChangeMappingGroup
    {
        public uint Id { get; set; }
        public int Disable { get; set; }
        public bool EvolvingExpInherit { get; set; }
        public int FailBonus { get; set; }
        public string Name { get; set; } = string.Empty;
        public bool Selectable { get; set; }
        public int Success { get; set; }
    }

    public sealed class ItemChangeMapping
    {
        public uint Id { get; set; }
        public uint MappingGroupId { get; set; }
        public int SourceGradeId { get; set; }
        public uint SourceItemId { get; set; }
        public int TargetGradeId { get; set; }
        public uint TargetItemId { get; set; }
    }

    public sealed class ItemAwakeningReactive
    {
        public uint ItemId { get; set; }
        public uint SkillId { get; set; }
        public uint MappingGroupId { get; set; }
        public int ConsumeCount { get; set; }
        public int LaborCost { get; set; }
        public int NativeValue2 { get; set; }
        public int NativeValue4 { get; set; }
    }

    public sealed class ItemRndAttrUnitModifierGroupSet
    {
        public uint Id { get; set; }
        public uint InheritPriorityId { get; set; }
        public uint CategoryId { get; set; }
        public string Name { get; set; } = string.Empty;
        public int PickCount { get; set; }
        public int Weight { get; set; }
    }

    public sealed class ItemRndAttrUnitModifierGroup
    {
        public uint Id { get; set; }
        public bool FixedAttribute { get; set; }
        public uint GroupSetId { get; set; }
        public uint UnitAttributeId { get; set; }
        public uint UnitModifierTypeId { get; set; }
        public int Weight { get; set; }
    }

    public sealed class ItemRndAttrUnitModifier
    {
        public uint Id { get; set; }
        public int GradeId { get; set; }
        public uint GroupId { get; set; }
        public int Maximum { get; set; }
        public int Minimum { get; set; }
    }

    public sealed class ItemEvolutionProfile
    {
        public uint ItemId { get; set; }
        public uint CategoryId { get; set; }
        public ItemRndAttrCategory Category { get; set; }
        public ItemRndAttrCategoryProperty Property { get; set; }
        public IReadOnlyList<ItemRndAttrCategoryElement> Elements { get; set; } =
            new List<ItemRndAttrCategoryElement>();
        public ItemEvolvingMaterial Material { get; set; }
        public IReadOnlyList<ItemChangeMapping> AwakeningMappings { get; set; } =
            new List<ItemChangeMapping>();
        public IReadOnlyList<uint> ValidMaterialItemIds { get; set; } =
            new List<uint>();
        public IReadOnlyList<ItemRndAttrUnitModifierGroupSet> ModifierGroupSets {
            get;
            set;
        } = new List<ItemRndAttrUnitModifierGroupSet>();

        public bool HasSynthesisDefinition => Category != null;
        public bool IsSynthesisMaterial => Material != null;
        public bool HasAwakeningDefinition => AwakeningMappings.Count > 0;
    }

    public interface IItemEvolutionRuleService
    {
        bool NativeCatalogueAvailable { get; }
        void Clear();
        void MarkNativeCatalogueAvailable();
        void RegisterItemCategory(uint itemId, uint categoryId);
        void RegisterCategoryGroup(ItemRndAttrCategoryGroup group);
        void RegisterCategoryRelation(ItemRndAttrCategoryRelation relation);
        void RegisterCategory(ItemRndAttrCategory category);
        void RegisterProperty(ItemRndAttrCategoryProperty property);
        void RegisterElement(ItemRndAttrCategoryElement element);
        void RegisterMaterial(ItemEvolvingMaterial material);
        void RegisterMappingGroup(ItemChangeMappingGroup group);
        void RegisterMapping(ItemChangeMapping mapping);
        void RegisterAwakeningReactive(ItemAwakeningReactive reactive);
        void RegisterRerollItem(uint itemSetId, uint itemId);
        void RegisterModifierGroupSet(ItemRndAttrUnitModifierGroupSet groupSet);
        void RegisterModifierGroup(ItemRndAttrUnitModifierGroup group);
        void RegisterModifier(ItemRndAttrUnitModifier modifier);
        ItemEvolutionProfile GetProfile(uint itemId, int gradeId);
        ItemChangeMappingGroup GetMappingGroup(uint id);
        ItemAwakeningReactive GetAwakeningReactive(uint itemId);
        IReadOnlyList<ItemAwakeningReactive> GetAwakeningReactives(
            uint mappingGroupId);
        bool IsRerollItem(uint itemSetId, uint itemId);
        ItemRndAttrUnitModifierGroup GetModifierGroup(uint id);
        ItemRndAttrUnitModifier GetModifierById(uint id);
        ItemRndAttrUnitModifier GetModifier(uint groupId, int gradeId);
        IReadOnlyList<ItemRndAttrUnitModifierGroup> GetModifierGroups(uint groupSetId);
    }

    /// <summary>
    /// Read-only authority for the native AA8 synthesis and awakening graph.
    /// Mutation remains disabled until its request/result protocol and all
    /// reagent/currency/failure semantics are confirmed from the AA8 client.
    /// </summary>
    public sealed class ItemEvolutionRuleService : IItemEvolutionRuleService
    {
        // Native AA8 category groups are paired by the client synthesis
        // catalogue. These are category-group relations, not item ids:
        // Ancient growth -> Ancient materials, Ancient T4-T5 growth ->
        // Ancient T4-T5 materials, and crafted weapon growth -> crafted
        // common/weapon materials.
        private static readonly IReadOnlyDictionary<uint, uint[]>
            NativeMaterialGroupsByTargetGroup =
                new Dictionary<uint, uint[]>
                {
                    [1] = new uint[] { 2 },
                    [11] = new uint[] { 12 },
                    [31] = new uint[] { 32 },
                    [33] = new uint[] { 34 },
                    [29] = new uint[] { 30 },
                    [21] = new uint[] { 24, 25 }
                };

        private readonly Dictionary<uint, uint> _itemCategories = new();
        private readonly Dictionary<uint, ItemRndAttrCategoryGroup> _categoryGroups = new();
        private readonly Dictionary<uint, HashSet<uint>> _relationsByTargetGroup = new();
        private readonly Dictionary<uint, ItemRndAttrCategory> _categories = new();
        private readonly Dictionary<(uint CategoryId, int GradeId), ItemRndAttrCategoryProperty>
            _properties = new();
        private readonly Dictionary<uint, List<ItemRndAttrCategoryElement>> _elements = new();
        private readonly Dictionary<uint, ItemEvolvingMaterial> _materials = new();
        private readonly Dictionary<uint, ItemChangeMappingGroup> _mappingGroups = new();
        private readonly Dictionary<uint, List<ItemChangeMapping>> _mappingsBySource = new();
        private readonly Dictionary<uint, ItemAwakeningReactive> _reactivesByItem =
            new();
        private readonly Dictionary<uint, List<ItemAwakeningReactive>>
            _reactivesByMappingGroup = new();
        private readonly Dictionary<uint, HashSet<uint>> _rerollItemsBySet =
            new();
        private readonly Dictionary<uint, ItemRndAttrUnitModifierGroupSet> _modifierGroupSets =
            new();
        private readonly Dictionary<uint, List<ItemRndAttrUnitModifierGroup>>
            _modifierGroupsBySet = new();
        private readonly Dictionary<uint, ItemRndAttrUnitModifierGroup> _modifierGroups =
            new();
        private readonly Dictionary<(uint GroupId, int GradeId), ItemRndAttrUnitModifier>
            _modifiers = new();
        private readonly Dictionary<uint, ItemRndAttrUnitModifier> _modifiersById =
            new();

        public static ItemEvolutionRuleService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _itemCategories.Clear();
            _categoryGroups.Clear();
            _relationsByTargetGroup.Clear();
            _categories.Clear();
            _properties.Clear();
            _elements.Clear();
            _materials.Clear();
            _mappingGroups.Clear();
            _mappingsBySource.Clear();
            _reactivesByItem.Clear();
            _reactivesByMappingGroup.Clear();
            _rerollItemsBySet.Clear();
            _modifierGroupSets.Clear();
            _modifierGroupsBySet.Clear();
            _modifierGroups.Clear();
            _modifiers.Clear();
            _modifiersById.Clear();
        }

        public void MarkNativeCatalogueAvailable()
        {
            NativeCatalogueAvailable = true;
        }

        public void RegisterItemCategory(uint itemId, uint categoryId)
        {
            if (categoryId > 0)
                _itemCategories[itemId] = categoryId;
        }

        public void RegisterCategoryGroup(ItemRndAttrCategoryGroup group)
        {
            if (group != null)
                _categoryGroups[group.Id] = group;
        }

        public void RegisterCategoryRelation(ItemRndAttrCategoryRelation relation)
        {
            if (relation == null)
                return;
            if (!_relationsByTargetGroup.TryGetValue(
                    relation.CategoryGroupId,
                    out var materialIds))
            {
                materialIds = new HashSet<uint>();
                _relationsByTargetGroup[relation.CategoryGroupId] = materialIds;
            }
            materialIds.Add(relation.MaterialItemId);
        }

        public void RegisterCategory(ItemRndAttrCategory category)
        {
            if (category != null)
                _categories[category.Id] = category;
        }

        public void RegisterProperty(ItemRndAttrCategoryProperty property)
        {
            if (property != null)
                _properties[(property.CategoryId, property.GradeId)] = property;
        }

        public void RegisterElement(ItemRndAttrCategoryElement element)
        {
            if (element == null)
                return;
            if (!_elements.TryGetValue(element.CategoryId, out var values))
            {
                values = new List<ItemRndAttrCategoryElement>();
                _elements[element.CategoryId] = values;
            }
            values.Add(element);
        }

        public void RegisterMaterial(ItemEvolvingMaterial material)
        {
            if (material != null)
                _materials[material.ItemId] = material;
        }

        public void RegisterMappingGroup(ItemChangeMappingGroup group)
        {
            if (group != null)
                _mappingGroups[group.Id] = group;
        }

        public void RegisterMapping(ItemChangeMapping mapping)
        {
            if (mapping == null)
                return;
            if (!_mappingsBySource.TryGetValue(mapping.SourceItemId, out var values))
            {
                values = new List<ItemChangeMapping>();
                _mappingsBySource[mapping.SourceItemId] = values;
            }
            values.Add(mapping);
        }

        public void RegisterAwakeningReactive(ItemAwakeningReactive reactive)
        {
            if (reactive == null || reactive.ItemId == 0 ||
                reactive.MappingGroupId == 0)
                return;
            _reactivesByItem[reactive.ItemId] = reactive;
            if (!_reactivesByMappingGroup.TryGetValue(
                    reactive.MappingGroupId,
                    out var rows))
            {
                rows = new List<ItemAwakeningReactive>();
                _reactivesByMappingGroup[reactive.MappingGroupId] = rows;
            }
            rows.RemoveAll(row => row.ItemId == reactive.ItemId);
            rows.Add(reactive);
        }

        public void RegisterRerollItem(uint itemSetId, uint itemId)
        {
            if (itemSetId == 0 || itemId == 0)
                return;
            if (!_rerollItemsBySet.TryGetValue(itemSetId, out var itemIds))
            {
                itemIds = new HashSet<uint>();
                _rerollItemsBySet[itemSetId] = itemIds;
            }
            itemIds.Add(itemId);
        }

        public bool IsRerollItem(uint itemSetId, uint itemId)
        {
            return itemSetId != 0 &&
                   _rerollItemsBySet.TryGetValue(itemSetId, out var itemIds) &&
                   itemIds.Contains(itemId);
        }

        public void RegisterModifierGroupSet(ItemRndAttrUnitModifierGroupSet groupSet)
        {
            if (groupSet != null)
                _modifierGroupSets[groupSet.Id] = groupSet;
        }

        public void RegisterModifierGroup(ItemRndAttrUnitModifierGroup group)
        {
            if (group == null)
                return;
            _modifierGroups[group.Id] = group;
            if (!_modifierGroupsBySet.TryGetValue(group.GroupSetId, out var values))
            {
                values = new List<ItemRndAttrUnitModifierGroup>();
                _modifierGroupsBySet[group.GroupSetId] = values;
            }
            values.Add(group);
        }

        public void RegisterModifier(ItemRndAttrUnitModifier modifier)
        {
            if (modifier != null)
            {
                _modifiers[(modifier.GroupId, modifier.GradeId)] = modifier;
                _modifiersById[modifier.Id] = modifier;
            }
        }

        public ItemEvolutionProfile GetProfile(uint itemId, int gradeId)
        {
            _materials.TryGetValue(itemId, out var material);
            var categoryId = _itemCategories.TryGetValue(itemId, out var equipmentCategory)
                ? equipmentCategory
                : material?.CategoryId ?? 0;
            _categories.TryGetValue(categoryId, out var category);
            _properties.TryGetValue((categoryId, gradeId), out var property);
            var elements = _elements.TryGetValue(categoryId, out var categoryElements)
                ? categoryElements.OrderBy(element => element.Level).ToList()
                : new List<ItemRndAttrCategoryElement>();
            var mappings = _mappingsBySource.TryGetValue(itemId, out var itemMappings)
                ? itemMappings
                    .Where(mapping =>
                        mapping.SourceGradeId < 0 || mapping.SourceGradeId == gradeId)
                    .OrderBy(mapping => mapping.MappingGroupId)
                    .ThenBy(mapping => mapping.Id)
                    .ToList()
                : new List<ItemChangeMapping>();
            var validMaterials = ResolveValidMaterials(category);
            var groupSets = GetModifierGroupSets(categoryId);

            return new ItemEvolutionProfile
            {
                ItemId = itemId,
                CategoryId = categoryId,
                Category = category,
                Property = property,
                Elements = elements,
                Material = material,
                AwakeningMappings = mappings,
                ValidMaterialItemIds = validMaterials,
                ModifierGroupSets = groupSets
            };
        }

        private IReadOnlyList<uint> ResolveValidMaterials(
            ItemRndAttrCategory category)
        {
            if (category == null)
                return new List<uint>();

            if (NativeMaterialGroupsByTargetGroup.TryGetValue(
                    category.CategoryGroupId,
                    out var nativeMaterialGroups))
            {
                var acceptedGroups = new HashSet<uint>(nativeMaterialGroups);
                return _materials.Values
                    .Where(material =>
                        _categories.TryGetValue(material.CategoryId,
                            out var materialCategory) &&
                        acceptedGroups.Contains(materialCategory.CategoryGroupId))
                    .Select(material => material.ItemId)
                    .Distinct()
                    .OrderBy(id => id)
                    .ToList();
            }

            return _relationsByTargetGroup.TryGetValue(
                    category.CategoryGroupId,
                    out var relationMaterialIds)
                ? relationMaterialIds.OrderBy(id => id).ToList()
                : new List<uint>();
        }

        public ItemChangeMappingGroup GetMappingGroup(uint id)
        {
            return _mappingGroups.TryGetValue(id, out var group) ? group : null;
        }

        public ItemAwakeningReactive GetAwakeningReactive(uint itemId)
        {
            return _reactivesByItem.TryGetValue(itemId, out var reactive)
                ? reactive
                : null;
        }

        public IReadOnlyList<ItemAwakeningReactive> GetAwakeningReactives(
            uint mappingGroupId)
        {
            return _reactivesByMappingGroup.TryGetValue(
                mappingGroupId,
                out var rows)
                ? rows.OrderBy(row => row.ItemId).ToList()
                : new List<ItemAwakeningReactive>();
        }

        public ItemRndAttrUnitModifierGroup GetModifierGroup(uint id)
        {
            return _modifierGroups.TryGetValue(id, out var group) ? group : null;
        }

        public ItemRndAttrUnitModifier GetModifierById(uint id)
        {
            return _modifiersById.TryGetValue(id, out var modifier)
                ? modifier
                : null;
        }

        public ItemRndAttrUnitModifier GetModifier(uint groupId, int gradeId)
        {
            return _modifiers.TryGetValue((groupId, gradeId), out var modifier)
                ? modifier
                : null;
        }

        public IReadOnlyList<ItemRndAttrUnitModifierGroup> GetModifierGroups(uint groupSetId)
        {
            return _modifierGroupsBySet.TryGetValue(groupSetId, out var values)
                ? values.OrderBy(value => value.Id).ToList()
                : new List<ItemRndAttrUnitModifierGroup>();
        }

        private IReadOnlyList<ItemRndAttrUnitModifierGroupSet> GetModifierGroupSets(
            uint categoryId)
        {
            // x2game mode-7 traverses group sets for the category and resolves
            // inherit_priority_id. Preserve both native category sets and their
            // ancestor chain, ordered deterministically.
            var selected = _modifierGroupSets.Values
                .Where(value => value.CategoryId == categoryId)
                .ToDictionary(value => value.Id);
            var frontier = selected.Values.ToList();
            foreach (var groupSet in frontier)
            {
                var parentId = groupSet.InheritPriorityId;
                var visited = new HashSet<uint>();
                while (parentId != 0 &&
                       visited.Add(parentId) &&
                       _modifierGroupSets.TryGetValue(parentId, out var parent))
                {
                    selected[parent.Id] = parent;
                    parentId = parent.InheritPriorityId;
                }
            }
            return selected.Values.OrderBy(value => value.Id).ToList();
        }
    }
}
