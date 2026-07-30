using System.Collections.Generic;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.Quests.Templates;


namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActSupplyItem : QuestActTemplate
    {
        public uint ItemId { get; set; }
        public int Count { get; set; }
        public byte GradeId { get; set; }
        public bool ShowActionBar { get; set; }
        public bool Cleanup { get; set; }
        public bool DropWhenDestroy { get; set; }
        public bool DestroyWhenDrop { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            _log.Warn("QuestActSupplyItem");
            var before = character.Inventory.GetItemsCount(ItemId);
            AA8ObservationService.Instance.TouchItem(character, ItemId);
            AA8ObservationService.Instance.RecordEvent(
                character,
                quest.Step == Static.QuestComponentKind.Reward ? "reward" : "supply",
                "attempted",
                "materialize_quest_item",
                quest.TemplateId,
                quest.ComponentId,
                nameof(QuestActSupplyItem),
                dependencyKind: "item",
                dependencyId: ItemId,
                expectedJson:
                    $"{{\"item_id\":{ItemId},\"count\":{Count},\"grade\":{GradeId}}}",
                actualJson: $"{{\"before\":{before}}}");
            //if (objective >= Count)
            //    return true;
            //else
            //{
            bool result;
            try
            {
                if (ItemManager.Instance.IsAutoEquipTradePack(ItemId))
                {
                    result = character.Inventory.TryEquipNewBackPack(
                        ItemTaskType.QuestSupplyItems,
                        ItemId,
                        Count,
                        GradeId);
                }
                else
                {
                    result = character.Inventory.Bag.AcquireDefaultItem(
                        ItemTaskType.QuestSupplyItems,
                        ItemId,
                        Count,
                        GradeId);
                }
            }
            catch (System.Exception ex)
            {
                AA8ObservationService.Instance.RecordEvent(
                    character,
                    quest.Step == Static.QuestComponentKind.Reward ? "reward" : "supply",
                    "blocked",
                    "materialize_quest_item",
                    quest.TemplateId,
                    quest.ComponentId,
                    nameof(QuestActSupplyItem),
                    dependencyKind: "item",
                    dependencyId: ItemId,
                    actualJson: $"{{\"before\":{before}}}",
                    blockerCode: "item_materialization_exception",
                    exception: ex);
                throw;
            }
            var after = character.Inventory.GetItemsCount(ItemId);
            AA8ObservationService.Instance.RecordEvent(
                character,
                quest.Step == Static.QuestComponentKind.Reward ? "reward" : "supply",
                result ? "executed" : "blocked",
                "materialize_quest_item",
                quest.TemplateId,
                quest.ComponentId,
                nameof(QuestActSupplyItem),
                dependencyKind: "item",
                dependencyId: ItemId,
                actualJson:
                    $"{{\"before\":{before},\"after\":{after},\"result\":{result.ToString().ToLowerInvariant()}}}",
                blockerCode: result ? null : "item_materialization_failed");
            return result;
            //    /*
            //    var template = ItemManager.Instance.GetTemplate(ItemId);
            //    if (template is BackpackTemplate backpackTemplate)
            //    {
            //        if (character.Inventory.TakeoffBackpack(ItemTaskType.QuestSupplyItems, true))
            //            return character.Inventory.Equipment.AcquireDefaultItem(ItemTaskType.QuestSupplyItems, ItemId, Count, GradeId);
            //        else
            //            return false;
            //    }
            //    else
            //    {
            //        return character.Inventory.Bag.AcquireDefaultItem(ItemTaskType.QuestSupplyItems, ItemId, Count, GradeId);
            //    }
            //    */

            //}
        }
    }
}
