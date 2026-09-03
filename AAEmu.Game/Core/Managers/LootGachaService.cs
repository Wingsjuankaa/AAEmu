using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Loots;
using AAEmu.Game.Models.Game.Skills;
using NLog;

namespace AAEmu.Game.Core.Managers;

/// <summary>Server-authoritative AA10 r575 Loot Gacha batch transaction.</summary>
public sealed class LootGachaService : Singleton<LootGachaService>
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();

    /// <summary>
    /// The AA10 retail UI derives its maximum from the smaller source/key stack and sends it as a
    /// u32. Inventory stack counts are signed ints in AAEmu, so that representation is the only
    /// server-side ceiling; the 1-10 range belongs to the native diagnostic command, not gameplay.
    /// </summary>
    public static bool IsSupportedBatchCount(uint requestedCount) =>
        requestedCount is > 0 and <= int.MaxValue;

    public bool Execute(
        Character character,
        SkillItem sourceCaster,
        SkillCastItemTarget consumeTarget,
        uint requestedCount,
        Random random = null)
    {
        if (character?.Inventory?.Bag is null ||
            FeaturesManager.Fsets?.Check(Feature.lootGacha) != true ||
            !IsSupportedBatchCount(requestedCount))
            return Fail(character, ErrorMessageType.FailedToUseItem);

        var bag = character.Inventory.Bag;
        lock (bag.Items)
        {
            var source = ResolveOwnedBagItem(character, sourceCaster?.ItemId ?? 0);
            var consume = ResolveOwnedBagItem(character, consumeTarget?.Id ?? 0);
            if (source is null || source.TemplateId != sourceCaster.ItemTemplateId || !source.CanDestroy())
                return Fail(character, source is { } && !source.CanDestroy()
                    ? ErrorMessageType.ItemSecureCondition
                    : ErrorMessageType.FailedToUseItem);

            var sourceStacks = GetConsumableStacks(bag, source.TemplateId, source);
            if (!CanSatisfyBatchFromStacks(requestedCount, sourceStacks.Select(item => item.Count)))
                return Fail(character, GetInsufficientStackError(bag, source.TemplateId, requestedCount));

            var consumeTemplateId = consume?.TemplateId ?? 0;
            if (!LootGachaGameData.Instance.TryGetActivePack(
                    source.TemplateId, consumeTemplateId, out var definition) ||
                (consume is not null && consumeTarget.Type1 != consume.TemplateId))
                return Fail(character, ErrorMessageType.FailedToUseItem);

            if (definition.ConsumeItemIds.Count > 0 &&
                (consume is null || !consume.CanDestroy()))
                return Fail(character, consume is { } && !consume.CanDestroy()
                    ? ErrorMessageType.ItemSecureCondition
                    : ErrorMessageType.FailedToUseItem);

            var consumeStacks = consume is null
                ? []
                : GetConsumableStacks(bag, consume.TemplateId, consume);
            if (consume is not null &&
                !CanSatisfyBatchFromStacks(requestedCount, consumeStacks.Select(item => item.Count)))
                return Fail(character, GetInsufficientStackError(bag, consume.TemplateId, requestedCount));

            var basePack = LootGameData.Instance.GetPack(definition.LootPackId);
            if (basePack is null)
                return Fail(character, ErrorMessageType.FailedToUseItem);

            var (savedTotal, savedLastRounds) = character.GachaRecords.Snapshot(definition.Id);
            var total = savedTotal;
            var lastRounds = new Dictionary<uint, uint>(savedLastRounds);
            var generatedRounds = new List<IReadOnlyList<(uint ItemId, int Count, byte Grade)>>();
            random ??= Random.Shared;

            for (var index = 0u; index < requestedCount; index++)
            {
                var generatedRound = new List<(uint ItemId, int Count, byte Grade)>();
                total = checked(total + 1);
                AddGenerated(generatedRound, basePack.GenerateGachaPack(character));

                var advanced = LootGachaCalculator.SelectAdvanced(
                    definition.AdvancedPacks, total, lastRounds, random);
                if (advanced is not null)
                {
                    var advancedPack = LootGameData.Instance.GetPack(advanced.LootPackId);
                    if (advancedPack is null)
                        return Fail(character, ErrorMessageType.FailedToUseItem);
                    AddGenerated(generatedRound, advancedPack.GenerateGachaPack(character));
                    lastRounds[advanced.Id] = total;
                }

                generatedRounds.Add(generatedRound);
            }

            var generated = generatedRounds.SelectMany(round => round).ToArray();
            var rewards = AggregateItemRewards(generated);
            var coins = generated.Where(entry => entry.ItemId == Item.Coins).Sum(entry => entry.Count);
            var roundResults = new List<(
                IReadOnlyList<GachaLootLogEntry> Logs,
                IReadOnlyList<Item> Items)>(generatedRounds.Count);
            try
            {
                foreach (var round in generatedRounds)
                {
                    var logs = round
                        .Where(entry => entry.Count > 0)
                        .GroupBy(entry => (entry.ItemId, entry.Grade))
                        .Select(group => new GachaLootLogEntry(
                            group.Key.ItemId,
                            group.Key.Grade,
                            group.Sum(entry => entry.Count)))
                        .ToArray();
                    roundResults.Add((logs, CreateResultItems(AggregateItemRewards(round))));
                }
            }
            catch (InvalidOperationException exception)
            {
                Logger.Error(exception, "AA10 Loot Gacha generated an invalid result before commit.");
                return Fail(character, ErrorMessageType.FailedToUseItem);
            }

            var consumedCount = checked((int)requestedCount);
            var freedSlots = CountFullyConsumedStacks(
                consumedCount, sourceStacks.Select(item => item.Count));
            if (consume is not null && !ReferenceEquals(source, consume))
                freedSlots += CountFullyConsumedStacks(
                    consumedCount, consumeStacks.Select(item => item.Count));
            if (!bag.CanAcquireDefaultItems(rewards, freedSlots, preserveExplicitGrade: true))
                return Fail(character, ErrorMessageType.BagFull);

            if (bag.ConsumeItem(
                    ItemTaskType.SkillEffectConsumption,
                    source.TemplateId,
                    consumedCount,
                    source) != requestedCount)
                return Fail(character, ErrorMessageType.NotEnoughRequiredItem);
            if (consume is not null && bag.ConsumeItem(
                    ItemTaskType.SkillEffectConsumption,
                    consume.TemplateId,
                    consumedCount,
                    consume) != requestedCount)
                throw new InvalidOperationException("Preflighted Loot Gacha key consumption failed.");

            foreach (var reward in rewards)
                if (!bag.AcquireDefaultItemEx(
                        ItemTaskType.SkillEffectGainItem,
                        reward.TemplateId,
                        reward.Amount,
                        reward.Grade,
                        out _,
                        out _,
                        0,
                        preserveExplicitGrade: true))
                    throw new InvalidOperationException("Preflighted Loot Gacha reward acquisition failed.");
            if (coins > 0)
                character.AddMoney(SlotType.Inventory, coins, ItemTaskType.SkillEffectGainItem);

            character.GachaRecords.Commit(definition.Id, total, lastRounds);
            for (var roundIndex = 0; roundIndex < roundResults.Count; roundIndex++)
            {
                var round = roundResults[roundIndex];
                var remainingBatchCount = requestedCount - (uint)roundIndex - 1;
                character.SendPacket(new SCGachaLootPackItemLogPacket(round.Logs));
                character.SendPacket(new SCGachaLootPackItemResultPacket(
                    ErrorMessageType.NoErrorMessage, remainingBatchCount, true, round.Items));
            }

            Logger.Info(
                "AA10 Loot Gacha: character={0}, pack={1}, count={2}, total={3}, rewards={4}, remaining=0",
                character.Id, definition.Id, requestedCount, total,
                string.Join(',', generated.Select(entry => $"{entry.ItemId}x{entry.Count}@{entry.Grade}")));
            return true;
        }
    }

    private static Item ResolveOwnedBagItem(Character character, ulong itemId)
    {
        if (itemId == 0)
            return null;
        var item = character.Inventory.Bag.GetItemByItemId(itemId);
        return item is not null && item.OwnerId == character.Id &&
               item.SlotType == SlotType.Inventory &&
               ReferenceEquals(item._holdingContainer, character.Inventory.Bag)
            ? item
            : null;
    }

    private static List<Item> GetConsumableStacks(ItemContainer bag, uint templateId, Item preferredItem)
    {
        bag.GetAllItemsByTemplate(templateId, -1, out var foundItems, out _);
        return foundItems
            .Where(item => item.CanDestroy())
            .OrderBy(item => ReferenceEquals(item, preferredItem) ? 0 : 1)
            .ThenBy(item => item.Slot)
            .ToList();
    }

    private static ErrorMessageType GetInsufficientStackError(
        ItemContainer bag, uint templateId, uint requestedCount)
    {
        bag.GetAllItemsByTemplate(templateId, -1, out _, out var totalCount);
        return totalCount >= requestedCount
            ? ErrorMessageType.ItemSecureCondition
            : ErrorMessageType.NotEnoughRequiredItem;
    }

    internal static bool CanSatisfyBatchFromStacks(
        uint requestedCount, IEnumerable<int> orderedStackCounts)
    {
        if (!IsSupportedBatchCount(requestedCount) || orderedStackCounts is null)
            return false;

        long available = 0;
        foreach (var stackCount in orderedStackCounts)
        {
            if (stackCount <= 0)
                continue;
            available += stackCount;
            if (available >= requestedCount)
                return true;
        }
        return false;
    }

    internal static int CountFullyConsumedStacks(
        int amountToConsume, IEnumerable<int> orderedStackCounts)
    {
        if (amountToConsume <= 0 || orderedStackCounts is null)
            return 0;

        var freedSlots = 0;
        foreach (var stackCount in orderedStackCounts)
        {
            if (stackCount <= 0 || amountToConsume <= 0)
                continue;
            if (amountToConsume >= stackCount)
                freedSlots++;
            amountToConsume -= Math.Min(amountToConsume, stackCount);
        }
        return freedSlots;
    }

    private static void AddGenerated(
        ICollection<(uint ItemId, int Count, byte Grade)> destination,
        IEnumerable<(uint itemId, int count, byte grade, uint originalGroup)> source)
    {
        foreach (var (itemId, count, grade, _) in source)
            if (itemId != 0 && count > 0)
                destination.Add((itemId, count, grade));
    }

    private static IReadOnlyList<Item> CreateResultItems(
        IEnumerable<(uint TemplateId, int Amount, int Grade)> rewards)
    {
        var result = new List<Item>();
        foreach (var reward in rewards)
        {
            var template = ItemManager.Instance.GetTemplate(reward.TemplateId);
            if (template is null)
                throw new InvalidOperationException(
                    $"Loot Gacha generated missing item template {reward.TemplateId}.");
            var remaining = reward.Amount;
            while (remaining > 0)
            {
                var count = Math.Min(remaining, template.MaxCount);
                var item = ItemManager.Instance.Create(
                    reward.TemplateId, count, (byte)reward.Grade, generateId: false);
                if (item is null)
                    throw new InvalidOperationException(
                        $"Loot Gacha could not create result descriptor {reward.TemplateId}.");
                result.Add(item);
                remaining -= count;
            }
        }
        if (result.Count > SCGachaLootPackItemResultPacket.MaximumItemCount)
            throw new InvalidOperationException("Loot Gacha result exceeds the native 15-item packet capacity.");
        return result;
    }

    private static (uint TemplateId, int Amount, int Grade)[] AggregateItemRewards(
        IEnumerable<(uint ItemId, int Count, byte Grade)> generated) =>
        generated
            .Where(entry => entry.ItemId != Item.Coins && entry.Count > 0)
            .GroupBy(entry => (entry.ItemId, entry.Grade))
            .Select(group => (
                TemplateId: group.Key.ItemId,
                Amount: group.Sum(entry => entry.Count),
                Grade: (int)group.Key.Grade))
            .ToArray();

    private static bool Fail(Character character, ErrorMessageType error)
    {
        character?.SendPacket(new SCGachaLootPackItemResultPacket(error, 0, true, []));
        return false;
    }
}
