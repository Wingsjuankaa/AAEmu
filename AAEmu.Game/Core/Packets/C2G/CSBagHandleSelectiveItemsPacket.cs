using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Core.Packets.C2G
{
    /// <summary>
    /// Kakao 8.0 native selective-item confirmation (opcode 0x1C4).
    /// The indices are one-based entries from the game11 selective_item list.
    /// </summary>
    public sealed class CSBagHandleSelectiveItemsPacket : GamePacket
    {
        public CSBagHandleSelectiveItemsPacket()
            : base(CSOffsets.CSBagHandleSelectiveItemsPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var slotType = (SlotType)stream.ReadByte();
            var slot = stream.ReadByte();
            var tryCount = stream.ReadUInt32();
            var optionCount = stream.ReadUInt32();

            if (optionCount == 0 || optionCount > 32)
            {
                Reject($"invalid option count {optionCount}", slotType, slot);
                return;
            }

            var selectedIndices = new List<uint>((int)optionCount);
            for (var index = 0; index < optionCount; index++)
                selectedIndices.Add(stream.ReadUInt32());

            var character = Connection.ActiveChar;
            if (character == null)
                return;
            if (slotType != SlotType.Inventory)
            {
                Reject($"unsupported source container {slotType}", slotType, slot);
                return;
            }

            var source = character.Inventory.Bag.GetItemBySlot(slot);
            if (source == null)
            {
                Reject("source slot is empty", slotType, slot);
                return;
            }

            var catalogue = SelectiveItemCatalogueService.Instance;
            if (!catalogue.TryGetBySourceItem(source.TemplateId, out var action))
            {
                Reject(
                    $"item {source.TemplateId} has no closed AA8 selective action",
                    slotType,
                    slot);
                return;
            }

            if (tryCount == 0 || (!action.IsMulti && tryCount != 1))
            {
                Reject(
                    $"tryCount {tryCount} is invalid for multi={action.IsMulti}",
                    slotType,
                    slot);
                return;
            }
            if (selectedIndices.Count != action.SelectCount ||
                selectedIndices.Distinct().Count() != selectedIndices.Count)
            {
                Reject(
                    $"selection count {selectedIndices.Count} does not match native count {action.SelectCount}",
                    slotType,
                    slot);
                return;
            }

            var selected = new List<SelectiveItemOption>(selectedIndices.Count);
            foreach (var optionIndex in selectedIndices)
            {
                if (!action.Options.TryGetValue(optionIndex, out var option))
                {
                    Reject($"unknown native option {optionIndex}", slotType, slot);
                    return;
                }
                selected.Add(option);
            }

            int sourceAmount;
            try
            {
                sourceAmount = checked(action.ConsumeItemCount * (int)tryCount);
            }
            catch (OverflowException)
            {
                Reject("source amount overflow", slotType, slot);
                return;
            }
            if (sourceAmount <= 0 || source.Count < sourceAmount)
            {
                Reject(
                    $"source count {source.Count} is below required {sourceAmount}",
                    slotType,
                    slot);
                return;
            }

            var products = new List<(SelectiveItemOption option, int amount, int grade)>();
            foreach (var option in selected)
            {
                int amount;
                try
                {
                    amount = checked(option.Count * (int)tryCount);
                }
                catch (OverflowException)
                {
                    Reject("result amount overflow", slotType, slot);
                    return;
                }

                var template = ItemManager.Instance.GetTemplate(option.ResultItemId);
                var coverage = ItemDefinitionCoverageService.Instance.Get(option.ResultItemId);
                if (template == null || !coverage.CanCreate)
                {
                    Reject(
                        $"AA8 result {option.ResultItemId} is not creatable ({coverage.State})",
                        slotType,
                        slot);
                    return;
                }

                var grade = option.Grade ?? source.Grade;
                if (template.FixedGrade >= 0 && !template.Gradable)
                    grade = template.FixedGrade;
                products.Add((option, amount, grade));
            }

            if (!HasCapacity(character.Inventory.Bag, source, sourceAmount, products))
            {
                Reject("inventory has insufficient post-exchange capacity", slotType, slot);
                return;
            }

            var before = character.Inventory.Bag.Items.ToDictionary(
                item => item.Id,
                item => new SelectiveItemSnapshot
                {
                    Id = item.Id,
                    SlotType = item.SlotType,
                    Slot = (byte)item.Slot,
                    TemplateId = item.TemplateId,
                    Count = item.Count
                });

            if (character.Inventory.Bag.ConsumeItem(
                    ItemTaskType.Invalid,
                    source.TemplateId,
                    sourceAmount,
                    source) != sourceAmount)
            {
                Reject("authoritative source consumption failed", slotType, slot);
                return;
            }

            foreach (var product in products)
            {
                if (!character.Inventory.Bag.AcquireDefaultItem(
                        ItemTaskType.Invalid,
                        product.option.ResultItemId,
                        product.amount,
                        product.grade))
                {
                    _log.Error(
                        "AA8 selective item {0} failed after validated mutation; forcing authoritative resync.",
                        action.SkillId);
                    character.Inventory.SendAuthoritativeContainer(SlotType.Inventory);
                    return;
                }
            }

            var after = character.Inventory.Bag.Items.ToDictionary(item => item.Id);
            var tasks = SelectiveItemDeltaBuilder.Build(before, after);

            if (tasks.Count == 0 || tasks.Count > 30)
            {
                _log.Error(
                    "AA8 selective item {0} produced invalid ItemTask count {1}; forcing resync.",
                    action.SkillId,
                    tasks.Count);
                character.Inventory.SendAuthoritativeContainer(SlotType.Inventory);
                return;
            }

            character.SendPacket(
                new SCItemTaskSuccessPacket(
                    ItemTaskType.SelectiveItem,
                    tasks,
                    new List<ulong>()));
            _log.Info(
                "AA8 selective item: character={0}, skill={1}, source={2}x{3}, tries={4}, options=[{5}]",
                character.Name,
                action.SkillId,
                source.TemplateId,
                sourceAmount,
                tryCount,
                string.Join(",", selectedIndices));
        }

        private static bool HasCapacity(
            ItemContainer bag,
            Item source,
            int sourceAmount,
            IEnumerable<(SelectiveItemOption option, int amount, int grade)> products)
        {
            var freeSlots = bag.FreeSlotCount + (source.Count == sourceAmount ? 1 : 0);
            var requiredNewSlots = 0;

            foreach (var group in products.GroupBy(
                         product => (product.option.ResultItemId, product.grade)))
            {
                var template = ItemManager.Instance.GetTemplate(group.Key.ResultItemId);
                if (template == null || template.MaxCount <= 0)
                    return false;

                var amount = group.Sum(product => product.amount);
                var existingCapacity = bag.Items
                    .Where(item =>
                        item.TemplateId == group.Key.ResultItemId &&
                        item.Grade == group.Key.grade &&
                        item.Id != source.Id)
                    .Sum(item => Math.Max(0, template.MaxCount - item.Count));
                var remainder = Math.Max(0, amount - existingCapacity);
                requiredNewSlots +=
                    (remainder + template.MaxCount - 1) / template.MaxCount;
            }

            // One source task plus at most 29 result tasks is the AA8 packet bound.
            return requiredNewSlots <= freeSlots && requiredNewSlots <= 29;
        }

        private void Reject(string reason, SlotType slotType, byte slot)
        {
            _log.Warn(
                "AA8 selective item rejected for {0}: {1} (slot={2}:{3})",
                Connection.ActiveChar?.Name ?? "<disconnected>",
                reason,
                slotType,
                slot);
            Connection.ActiveChar?.Inventory.SendAuthoritativeContainer(slotType);
        }
    }
}
