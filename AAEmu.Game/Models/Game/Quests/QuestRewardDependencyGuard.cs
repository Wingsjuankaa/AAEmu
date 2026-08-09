using System;
using System.Collections.Generic;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;

namespace AAEmu.Game.Models.Game.Quests
{
    /// <summary>
    /// Validates the complete reward set before any reward act mutates the
    /// character. This prevents partial/duplicate payouts and rejects the AA8
    /// sentinel selection 0 when a selective reward is mandatory.
    /// </summary>
    public static class QuestRewardDependencyGuard
    {
        public static bool CanComplete(
            Quest quest,
            int selected,
            out uint unavailableItemId,
            out string reason)
        {
            unavailableItemId = 0;
            reason = string.Empty;
            if (quest?.Template == null || quest.Owner == null)
            {
                reason = "missing_quest_state";
                return false;
            }

            var fixedRewards = new List<QuestActSupplyItem>();
            var selectiveRewards = new List<QuestActSupplySelectiveItem>();
            foreach (var component in
                     quest.Template.GetComponents(QuestComponentKind.Reward))
            {
                foreach (var act in QuestManager.Instance.GetActs(component.Id))
                {
                    if (act.DetailType == nameof(QuestActSupplyItem))
                    {
                        var reward = act.GetTemplate<QuestActSupplyItem>();
                        if (reward != null)
                            fixedRewards.Add(reward);
                    }
                    else if (act.DetailType ==
                             nameof(QuestActSupplySelectiveItem))
                    {
                        var reward =
                            act.GetTemplate<QuestActSupplySelectiveItem>();
                        if (reward != null)
                            selectiveRewards.Add(reward);
                    }
                }
            }

            if (!IsValidSelection(selected, selectiveRewards.Count))
            {
                reason = "invalid_selective_reward";
                return false;
            }

            var rewards =
                new Dictionary<(uint ItemId, byte GradeId), int>();
            foreach (var reward in fixedRewards)
            {
                var key = (reward.ItemId, reward.GradeId);
                rewards[key] =
                    rewards.TryGetValue(key, out var count)
                        ? count + reward.Count
                        : reward.Count;
            }
            if (selectiveRewards.Count > 0)
            {
                var reward = selectiveRewards[selected - 1];
                var key = (reward.ItemId, reward.GradeId);
                rewards[key] =
                    rewards.TryGetValue(key, out var count)
                        ? count + reward.Count
                        : reward.Count;
            }

            var requiredBagSlots = 0;
            foreach (var reward in rewards)
            {
                var itemTemplate =
                    ItemManager.Instance.GetTemplate(reward.Key.ItemId);
                var coverageService = ItemDefinitionCoverageService.Instance;
                var coverage = coverageService.Get(reward.Key.ItemId);
                if (!EvaluateRewardItemDefinition(
                        itemTemplate != null,
                        coverageService.NativeCatalogueAvailable,
                        coverage.State,
                        coverageService.PhaseACandidateTestCreationAllowed))
                {
                    unavailableItemId = reward.Key.ItemId;
                    reason = itemTemplate == null
                        ? "missing_item_template"
                        : $"item_coverage_{coverage.State}";
                    return false;
                }

                if (reward.Value <= 0 ||
                    ItemManager.Instance.IsAutoEquipTradePack(
                        reward.Key.ItemId))
                    continue;

                quest.Owner.Inventory.Bag.GetAllItemsByTemplate(
                    reward.Key.ItemId,
                    reward.Key.GradeId,
                    out var currentItems,
                    out var currentCount);
                var maxCount = Math.Max(1, itemTemplate.MaxCount);
                var existingSpace =
                    currentItems.Count * maxCount - currentCount;
                var unitsNeedingSlots =
                    Math.Max(0, reward.Value - existingSpace);
                requiredBagSlots +=
                    (unitsNeedingSlots + maxCount - 1) / maxCount;
            }

            if (requiredBagSlots > quest.Owner.Inventory.Bag.FreeSlotCount)
            {
                reason = "insufficient_bag_space";
                return false;
            }

            return true;
        }

        public static bool IsValidSelection(
            int selected,
            int selectiveRewardCount)
        {
            return selectiveRewardCount == 0
                ? selected == 0
                : selected >= 1 && selected <= selectiveRewardCount;
        }

        public static bool EvaluateRewardItemDefinition(
            bool itemTemplateExists,
            bool nativeCatalogueAvailable,
            ItemDefinitionCoverageState coverageState,
            bool phaseACandidateCreationAllowed)
        {
            if (!itemTemplateExists)
                return false;
            if (!nativeCatalogueAvailable)
                return true;
            if (coverageState == ItemDefinitionCoverageState.Complete)
                return true;
            return coverageState == ItemDefinitionCoverageState.PhaseACandidate &&
                   phaseACandidateCreationAllowed;
        }
    }
}
