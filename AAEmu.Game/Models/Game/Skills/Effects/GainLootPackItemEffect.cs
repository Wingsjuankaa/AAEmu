using System;
using System.Collections.Generic;
using System.Linq;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class GainLootPackItemEffect : EffectTemplate
    {
        public uint LootPackId { get; set; }
        public bool ConsumeSourceItem { get; set; }
        public uint ConsumeItemId { get; set; }
        public int ConsumeCount { get; set; }
        public bool InheritGrade { get; set; }

        public override bool OnActionTime => false;

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj,
            EffectSource source, SkillObject skillObject, DateTime time, CompressedGamePackets packetBuilder = null)
        {
            if (caster is not Character character)
                return;

            var lootPacks = ItemManager.Instance.GetLootPacks(LootPackId);
            var lootGroups = ItemManager.Instance.GetLootGroups(LootPackId);

            Item sourceItem = null;
            if (casterObj is SkillItem skillItem)
                sourceItem = character.Inventory.Bag.GetItemByItemId(skillItem.ItemId);

            if (ConsumeSourceItem && sourceItem == null)
            {
                _log.Warn(
                    "Cannot apply loot pack {0}: source item is required but the caster is {1}",
                    LootPackId,
                    casterObj?.GetType().Name ?? "null");
                if (source?.Skill != null)
                    source.Skill.Cancelled = true;
                return;
            }

            if (InheritGrade && sourceItem == null)
            {
                _log.Warn(
                    "Cannot apply loot pack {0}: grade inheritance requires a source item",
                    LootPackId);
                if (source?.Skill != null)
                    source.Skill.Cancelled = true;
                return;
            }

            var sourceTemplateId = sourceItem?.TemplateId ?? 0;

            _log.Trace("LootGroups {0}", string.Join(',', lootGroups.Select(x => x.Id)));

            var rowG = lootGroups.Length;
            var rowP = lootPacks.Length;
            if (rowG == 0 && rowP == 0)
            {
                _log.Error(
                    "Cannot apply loot pack {0} for item template {1}: no loot or loot-group rows were loaded; source item will not be consumed",
                    LootPackId,
                    sourceTemplateId);
                if (source?.Skill != null)
                    source.Skill.Cancelled = true;
                return;
            }

            // Loot-pack effects run before Skill consumes the source item.
            // Reserve enough currently-free slots for every independently
            // selected non-currency group so a multi-result box can never
            // grant a prefix of its contents and then fail midway.
            var requiredResultSlots = lootPacks
                .Where(row => row.ItemId != Item.Coins)
                .Select(row => row.Group)
                .Distinct()
                .Count();
            if (requiredResultSlots > character.Inventory.Bag.FreeSlotCount)
            {
                _log.Warn(
                    "Cannot apply loot pack {0} for item template {1}: " +
                    "requires {2} free result slots, has {3}",
                    LootPackId,
                    sourceTemplateId,
                    requiredResultSlots,
                    character.Inventory.Bag.FreeSlotCount);
                character.SendErrorMessage(ErrorMessageType.BagFull);
                if (source?.Skill != null)
                    source.Skill.Cancelled = true;
                return;
            }

            if (rowG >= 1)
            {
                const float maxDropRate = (float)10000000;
                for (var i = 0; i < rowG; i++)
                {
                    var itemIdLoot = (uint)0;
                    var minAmount = 0;
                    var maxAmount = 0;
                    var gradeId = (byte)0;
                    var dropRateMax = (uint)0;
                    var dropRate = Rand.Next(0, maxDropRate);
                    var dropRateGroup = (uint)10000000;
                    if (lootGroups[i].GroupNo > 1 && rowG >= 2)
                    {
                        dropRateGroup = 0;
                        for (var di = 0; di < lootGroups[i].GroupNo; di++)
                            if (lootGroups[di].GroupNo > 1)
                                dropRateGroup += lootGroups[di].DropRate;
                    }

                    if (dropRateGroup >= dropRate)
                    {
                        for (var ui = 0; ui < rowP; ui++)
                        {
                            if (lootPacks[ui].Group == lootGroups[i].GroupNo)
                            {
                                dropRateMax += lootPacks[ui].DropRate;
                            }
                        }

                        var dropRateItem = Rand.Next(0, dropRateMax);
                        var dropRateItemId = (uint)0;
                        for (var uii = 0; uii < rowP; uii++)
                        {
                            if (lootPacks[uii].Group == lootGroups[i].GroupNo)
                            {
                                if (lootPacks[uii].DropRate + dropRateItemId >= dropRateItem)
                                {
                                    itemIdLoot = lootPacks[uii].ItemId;
                                    minAmount = lootPacks[uii].MinAmount;
                                    maxAmount = lootPacks[uii].MaxAmount;
                                    gradeId = lootPacks[uii].GradeId;
                                    uii = rowP;
                                }
                                else
                                {
                                    dropRateItemId += lootPacks[uii].DropRate;
                                }
                            }
                        }
                    }

                    if (minAmount > 1 && itemIdLoot == Item.Coins)
                    {
                        AddGold(caster, minAmount, maxAmount);
                    }

                    if (itemIdLoot > 0 && itemIdLoot != Item.Coins)
                    {
                        if (InheritGrade)
                            gradeId = sourceItem.Grade;

                        if (lootGroups[i].ItemGradeDistributionId > 0)
                        {
                            if (!TryGetGradeDistributionId(
                                    lootGroups[i].ItemGradeDistributionId,
                                    out gradeId))
                            {
                                source.Skill.Cancelled = true;
                                continue;
                            }
                        }

                        AddItem(caster, itemIdLoot, gradeId, minAmount, maxAmount, sourceItem);
                    }
                }
            }
            else
            {
                if (rowP >= 1)
                {
                    for (var i = 1; i <= 17; i++) ////////max group here ////// in sqlite max group = 17 /////
                    {
                        var itemIdLoot = (uint)0;
                        var minAmount = 0;
                        var maxAmount = 0;
                        var gradeId = (byte)0;
                        var dropRateMax = (uint)0;
                        for (var ui = 0; ui < rowP; ui++)
                            if (lootPacks[ui].Group == i)
                                dropRateMax += lootPacks[ui].DropRate;

                        var dropRateItem = Rand.Next(0, dropRateMax);
                        var dropRateItemId = (uint)0;
                        for (var uii = 0; uii < rowP; uii++)
                        {
                            if (lootPacks[uii].Group == i)
                            {
                                if (lootPacks[uii].DropRate + dropRateItemId >= dropRateItem)
                                {
                                    itemIdLoot = lootPacks[uii].ItemId;
                                    minAmount = lootPacks[uii].MinAmount;
                                    maxAmount = lootPacks[uii].MaxAmount;
                                    gradeId = lootPacks[uii].GradeId;
                                    uii = rowP;
                                }
                                else
                                {
                                    dropRateItemId += lootPacks[uii].DropRate;
                                }
                            }
                        }

                        if (minAmount > 1 && itemIdLoot == 500)
                            AddGold(caster, minAmount, maxAmount);

                        if (itemIdLoot > 0 && itemIdLoot != 500)
                        {
                            if (InheritGrade)
                                gradeId = sourceItem.Grade;

                            AddItem(caster, itemIdLoot, gradeId, minAmount, maxAmount, sourceItem);
                        }
                    }
                }
            }

            //if (sourceItem != null)
            //    character.Inventory.Bag.ConsumeItem(ItemTaskType.ConsumeSkillSource, sourceItem.TemplateId, 1, sourceItem);   

            _log.Trace("GainLootPackItemEffect {0}", LootPackId);
        }

        private void AddGold(Unit caster, int goldMin, int goldMax)
        {
            var character = (Character)caster;
            if (character == null) return;
            var goldAdd = Rand.Next(goldMin, goldMax);
            var jackpot = Rand.Next(0, 10000);
            if (jackpot <= 50)
                goldAdd = goldAdd * 1000;

            if (jackpot <= 5)
                goldAdd = goldAdd * 5000;

            character.Money += goldAdd;
            character.SendPacket(new SCItemTaskSuccessPacket(ItemTaskType.SkillEffectGainItem,
                new List<ItemTask> {new MoneyChange(goldAdd)}, new List<ulong>()));
        }

        private void AddItem(Unit caster, uint itemId, byte gradeId, int minAmount, int maxAmount,
            Item sourceItem = null)
        {
            var character = (Character)caster;
            if (character == null) return;
            var amount = Rand.Next(minAmount, maxAmount);
            var template = ItemManager.Instance.GetTemplate(itemId);
            if (template?.LootQuestId > 0 &&
                !character.Quests.CanAcquireQuestLoot(
                    template.LootQuestId,
                    itemId,
                    amount))
            {
                _log.Warn(
                    "[AA8QuestLootGuard] Rejected quest loot: character={0}, " +
                    "quest={1}, item={2}, amount={3}; no matching incomplete " +
                    "Progress objective remains.",
                    character.Name,
                    template.LootQuestId,
                    itemId,
                    amount);
                return;
            }
            if (!character.Inventory.Bag.AcquireDefaultItem(ItemTaskType.Loot, itemId, amount, gradeId))
            {
                // TODO: do proper handling of insufficient bag space
                character.SendErrorMessage(ErrorMessageType.BagFull);
            }
            /*
            else
            {
                if(ConsumeSourceItem)
                {
                    character.Inventory.Bag.RemoveItem(ItemTaskType.ConsumeSkillSource, sourceItem, true);
                }
                else
                {
                    character.Inventory.Bag.ConsumeItem(ItemTaskType.ConsumeSkillSource, ConsumeItemId, ConsumeCount, sourceItem);
                }
            }
            */
        }

        private bool TryGetGradeDistributionId(byte distributionId, out byte gradeId)
        {
            gradeId = 0;
            var gradeDist = ItemManager.Instance.GetGradeDistributions(distributionId);
            if (gradeDist == null)
            {
                _log.Error(
                    "Native AA8 item-grade distribution {0} was not loaded; loot generation cancelled",
                    distributionId);
                return false;
            }

            var totalWeight = GradeDistributionSelector.GetTotalWeight(gradeDist);
            if (totalWeight <= 0)
            {
                _log.Error(
                    "Native AA8 item-grade distribution {0} has no positive weights; loot generation cancelled",
                    distributionId);
                return false;
            }

            gradeId = GradeDistributionSelector.SelectByRoll(
                gradeDist,
                Rand.Next(0, totalWeight));
            return true;
        }
    }
}
