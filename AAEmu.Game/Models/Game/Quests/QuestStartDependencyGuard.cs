using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests
{
    /// <summary>
    /// Prevents a quest from entering the journal when one of its initial
    /// SupplyItem dependencies cannot be created by the active runtime.
    /// Reward items are intentionally outside this preflight because they are
    /// validated when the quest is completed.
    /// </summary>
    public static class QuestStartDependencyGuard
    {
        public static bool CanStart(
            QuestTemplate template,
            out uint unavailableItemId,
            out string reason)
        {
            unavailableItemId = 0;
            reason = string.Empty;
            if (template == null)
            {
                reason = "missing_quest_template";
                return false;
            }

            foreach (var component in template.GetComponents(QuestComponentKind.Supply))
            {
                foreach (var act in QuestManager.Instance.GetActs(component.Id))
                {
                    if (act.DetailType != nameof(QuestActSupplyItem))
                        continue;

                    var supply = act.GetTemplate<QuestActSupplyItem>();
                    if (supply == null)
                    {
                        reason = "missing_supply_act";
                        return false;
                    }

                    var itemTemplateExists =
                        ItemManager.Instance.GetTemplate(supply.ItemId) != null;
                    var coverageService = ItemDefinitionCoverageService.Instance;
                    var coverage = coverageService.Get(supply.ItemId);
                    if (EvaluateSupplyItemDefinition(
                            itemTemplateExists,
                            coverageService.NativeCatalogueAvailable,
                            coverage.State))
                        continue;

                    unavailableItemId = supply.ItemId;
                    reason = !itemTemplateExists
                        ? "missing_item_template"
                        : $"item_coverage_{coverage.State}";
                    return false;
                }
            }

            return true;
        }

        public static bool EvaluateSupplyItemDefinition(
            bool itemTemplateExists,
            bool nativeCatalogueAvailable,
            ItemDefinitionCoverageState coverageState)
        {
            if (!itemTemplateExists)
                return false;

            return !nativeCatalogueAvailable ||
                   coverageState == ItemDefinitionCoverageState.Complete;
        }
    }
}
