using System;
using System.Collections.Generic;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class SelectiveItemOption
    {
        public uint Index { get; set; }
        public uint ResultItemId { get; set; }
        public int Count { get; set; }
        public int? Grade { get; set; }
        public string ResultUid { get; set; } = string.Empty;
        public string Provenance { get; set; } = string.Empty;
    }

    public sealed class SelectiveItemAction
    {
        public uint SkillId { get; set; }
        public uint SourceItemId { get; set; }
        public string Alias { get; set; } = string.Empty;
        public int SelectCount { get; set; }
        public int ConsumeItemCount { get; set; }
        public bool IsMulti { get; set; }
        public string PopupText { get; set; } = string.Empty;
        public string Provenance { get; set; } = string.Empty;
        public Dictionary<uint, SelectiveItemOption> Options { get; } = new();
    }

    public interface ISelectiveItemCatalogueService
    {
        bool NativeCatalogueAvailable { get; }
        void Clear();
        void RegisterAction(SelectiveItemAction action);
        void RegisterOption(uint skillId, SelectiveItemOption option);
        bool TryGetBySkill(uint skillId, out SelectiveItemAction action);
        bool TryGetBySourceItem(uint itemId, out SelectiveItemAction action);
    }

    public sealed class SelectiveItemCatalogueService : ISelectiveItemCatalogueService
    {
        private readonly Dictionary<uint, SelectiveItemAction> _bySkill = new();
        private readonly Dictionary<uint, SelectiveItemAction> _bySourceItem = new();

        public static SelectiveItemCatalogueService Instance { get; } = new();
        public bool NativeCatalogueAvailable => _bySkill.Count > 0;

        public void Clear()
        {
            _bySkill.Clear();
            _bySourceItem.Clear();
        }

        public void RegisterAction(SelectiveItemAction action)
        {
            if (action == null)
                throw new ArgumentNullException(nameof(action));
            _bySkill[action.SkillId] = action;
            _bySourceItem[action.SourceItemId] = action;
        }

        public void RegisterOption(uint skillId, SelectiveItemOption option)
        {
            if (option == null)
                throw new ArgumentNullException(nameof(option));
            if (!_bySkill.TryGetValue(skillId, out var action))
                throw new InvalidOperationException(
                    $"AA8 selective option references missing skill {skillId}.");
            action.Options[option.Index] = option;
        }

        public bool TryGetBySkill(uint skillId, out SelectiveItemAction action) =>
            _bySkill.TryGetValue(skillId, out action);

        public bool TryGetBySourceItem(uint itemId, out SelectiveItemAction action) =>
            _bySourceItem.TryGetValue(itemId, out action);
    }
}
