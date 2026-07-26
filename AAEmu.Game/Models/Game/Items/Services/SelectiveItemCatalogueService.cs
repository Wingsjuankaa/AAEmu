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
        void RegisterOption(uint sourceItemId, SelectiveItemOption option);
        bool TryGetBySkill(uint skillId, out SelectiveItemAction action);
        bool TryGetBySourceItem(uint itemId, out SelectiveItemAction action);
    }

    public sealed class SelectiveItemCatalogueService : ISelectiveItemCatalogueService
    {
        private readonly Dictionary<uint, List<SelectiveItemAction>> _bySkill = new();
        private readonly Dictionary<uint, SelectiveItemAction> _bySourceItem = new();

        public static SelectiveItemCatalogueService Instance { get; } = new();
        public bool NativeCatalogueAvailable => _bySourceItem.Count > 0;

        public void Clear()
        {
            _bySkill.Clear();
            _bySourceItem.Clear();
        }

        public void RegisterAction(SelectiveItemAction action)
        {
            if (action == null)
                throw new ArgumentNullException(nameof(action));
            if (_bySourceItem.ContainsKey(action.SourceItemId))
                throw new InvalidOperationException(
                    $"AA8 selective action duplicates source item {action.SourceItemId}.");
            if (!_bySkill.TryGetValue(action.SkillId, out var actions))
            {
                actions = new List<SelectiveItemAction>();
                _bySkill.Add(action.SkillId, actions);
            }
            actions.Add(action);
            _bySourceItem[action.SourceItemId] = action;
        }

        public void RegisterOption(uint sourceItemId, SelectiveItemOption option)
        {
            if (option == null)
                throw new ArgumentNullException(nameof(option));
            if (!_bySourceItem.TryGetValue(sourceItemId, out var action))
                throw new InvalidOperationException(
                    $"AA8 selective option references missing source item {sourceItemId}.");
            action.Options[option.Index] = option;
        }

        public bool TryGetBySkill(uint skillId, out SelectiveItemAction action)
        {
            action = null;
            return _bySkill.TryGetValue(skillId, out var actions) &&
                   actions.Count == 1 &&
                   (action = actions[0]) != null;
        }

        public bool TryGetBySourceItem(uint itemId, out SelectiveItemAction action) =>
            _bySourceItem.TryGetValue(itemId, out action);
    }
}
