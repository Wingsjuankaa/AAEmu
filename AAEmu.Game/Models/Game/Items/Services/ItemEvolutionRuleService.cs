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
        void RegisterCategory(ItemRndAttrCategory category);
        void RegisterProperty(ItemRndAttrCategoryProperty property);
        void RegisterElement(ItemRndAttrCategoryElement element);
        void RegisterMaterial(ItemEvolvingMaterial material);
        void RegisterMappingGroup(ItemChangeMappingGroup group);
        void RegisterMapping(ItemChangeMapping mapping);
        ItemEvolutionProfile GetProfile(uint itemId, int gradeId);
        ItemChangeMappingGroup GetMappingGroup(uint id);
    }

    /// <summary>
    /// Read-only authority for the native AA8 synthesis and awakening graph.
    /// Mutation remains disabled until its request/result protocol and all
    /// reagent/currency/failure semantics are confirmed from the AA8 client.
    /// </summary>
    public sealed class ItemEvolutionRuleService : IItemEvolutionRuleService
    {
        private readonly Dictionary<uint, uint> _itemCategories = new();
        private readonly Dictionary<uint, ItemRndAttrCategory> _categories = new();
        private readonly Dictionary<(uint CategoryId, int GradeId), ItemRndAttrCategoryProperty>
            _properties = new();
        private readonly Dictionary<uint, List<ItemRndAttrCategoryElement>> _elements = new();
        private readonly Dictionary<uint, ItemEvolvingMaterial> _materials = new();
        private readonly Dictionary<uint, ItemChangeMappingGroup> _mappingGroups = new();
        private readonly Dictionary<uint, List<ItemChangeMapping>> _mappingsBySource = new();

        public static ItemEvolutionRuleService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _itemCategories.Clear();
            _categories.Clear();
            _properties.Clear();
            _elements.Clear();
            _materials.Clear();
            _mappingGroups.Clear();
            _mappingsBySource.Clear();
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

            return new ItemEvolutionProfile
            {
                ItemId = itemId,
                CategoryId = categoryId,
                Category = category,
                Property = property,
                Elements = elements,
                Material = material,
                AwakeningMappings = mappings
            };
        }

        public ItemChangeMappingGroup GetMappingGroup(uint id)
        {
            return _mappingGroups.TryGetValue(id, out var group) ? group : null;
        }
    }
}
