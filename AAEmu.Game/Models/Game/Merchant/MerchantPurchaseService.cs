using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Merchant
{
    public sealed class MerchantPurchaseRequest
    {
        public uint ItemId { get; set; }
        public byte Grade { get; set; }
        public int Count { get; set; }
        public ShopCurrencyType Currency { get; set; }
    }

    public sealed class MerchantPurchaseLine
    {
        public uint ItemId { get; set; }
        public byte Grade { get; set; }
        public int Count { get; set; }
        public ShopCurrencyType Currency { get; set; }
        public int UnitPrice { get; set; }
    }

    public sealed class MerchantPurchasePlan
    {
        public IReadOnlyList<MerchantPurchaseLine> Lines { get; internal set; }
        public long Money { get; internal set; }
        public long Honor { get; internal set; }
        public long Vocation { get; internal set; }
    }

    public interface IMerchantPurchaseService
    {
        bool TryPrepare(
            Character character,
            MerchantGoods stock,
            IEnumerable<MerchantPurchaseRequest> requests,
            out MerchantPurchasePlan plan,
            out string rejection);

        bool TryCommit(
            Character character,
            MerchantPurchasePlan plan,
            out string rejection);
    }

    public sealed class MerchantPurchaseService : IMerchantPurchaseService
    {
        public static MerchantPurchaseService Instance { get; } = new();

        public bool TryPrepare(
            Character character,
            MerchantGoods stock,
            IEnumerable<MerchantPurchaseRequest> requests,
            out MerchantPurchasePlan plan,
            out string rejection)
        {
            plan = null;
            rejection = string.Empty;
            if (character == null || stock == null || requests == null)
                return Reject("missing character or authoritative stock", out rejection);

            var lines = new List<MerchantPurchaseLine>();
            foreach (var request in requests)
            {
                if (request == null || request.Count <= 0)
                    return Reject("purchase quantity must be positive", out rejection);

                var stockItem = stock.GetStock(
                    request.ItemId,
                    request.Grade,
                    request.Currency);
                if (stockItem == null)
                    return Reject(
                        $"item {request.ItemId} grade {request.Grade} currency " +
                        $"{request.Currency} is not in the authoritative stock",
                        out rejection);

                var template = ItemManager.Instance.GetTemplate(request.ItemId);
                var coverage = ItemDefinitionCoverageService.Instance.Get(request.ItemId);
                if (template == null ||
                    (ItemDefinitionCoverageService.Instance.NativeCatalogueAvailable &&
                     !coverage.CanCreate))
                    return Reject(
                        $"item {request.ItemId} is not a complete AA8 definition",
                        out rejection);

                var unitPrice = stockItem.Price >= 0
                    ? stockItem.Price
                    : GetTemplatePrice(template, stockItem.Currency);
                if (unitPrice < 0)
                    return Reject($"item {request.ItemId} has a negative price", out rejection);

                lines.Add(
                    new MerchantPurchaseLine
                    {
                        ItemId = request.ItemId,
                        Grade = stockItem.Grade,
                        Count = request.Count,
                        Currency = stockItem.Currency,
                        UnitPrice = unitPrice
                    });
            }

            if (lines.Count == 0)
                return Reject("empty purchase", out rejection);
            if (!TryCalculateTotals(
                    lines,
                    out var money,
                    out var honor,
                    out var vocation,
                    out rejection))
                return false;
            if (money > character.Money ||
                honor > character.HonorPoint ||
                vocation > character.VocationPoint)
                return Reject("insufficient funds", out rejection);
            if (money > int.MaxValue || honor > int.MaxValue || vocation > int.MaxValue)
                return Reject("purchase total exceeds runtime currency bounds", out rejection);
            if (!HasCapacity(character.Inventory.Bag, lines))
                return Reject("inventory has insufficient capacity", out rejection);

            plan = new MerchantPurchasePlan
            {
                Lines = lines,
                Money = money,
                Honor = honor,
                Vocation = vocation
            };
            return true;
        }

        public static bool TryCalculateTotals(
            IEnumerable<MerchantPurchaseLine> lines,
            out long money,
            out long honor,
            out long vocation,
            out string rejection)
        {
            money = 0;
            honor = 0;
            vocation = 0;
            rejection = string.Empty;
            if (lines == null)
                return Reject("missing purchase lines", out rejection);
            try
            {
                foreach (var line in lines)
                {
                    if (line == null || line.Count <= 0 || line.UnitPrice < 0)
                        return Reject(
                            "purchase line has invalid quantity or price",
                            out rejection);
                    var linePrice = checked((long)line.UnitPrice * line.Count);
                    switch (line.Currency)
                    {
                        case ShopCurrencyType.Money:
                            money = checked(money + linePrice);
                            break;
                        case ShopCurrencyType.Honor:
                            honor = checked(honor + linePrice);
                            break;
                        case ShopCurrencyType.VocationBadges:
                            vocation = checked(vocation + linePrice);
                            break;
                        default:
                            return Reject(
                                $"unsupported authoritative currency {line.Currency}",
                                out rejection);
                    }
                }
            }
            catch (OverflowException)
            {
                return Reject("purchase total overflow", out rejection);
            }
            return true;
        }

        public bool TryCommit(
            Character character,
            MerchantPurchasePlan plan,
            out string rejection)
        {
            rejection = string.Empty;
            if (character == null || plan?.Lines == null || plan.Lines.Count == 0)
                return Reject("missing purchase plan", out rejection);

            lock (character.Inventory.Bag)
            {
                if (plan.Money > character.Money ||
                    plan.Honor > character.HonorPoint ||
                    plan.Vocation > character.VocationPoint)
                    return Reject("funds changed before commit", out rejection);
                if (!HasCapacity(character.Inventory.Bag, plan.Lines))
                    return Reject("inventory changed before commit", out rejection);

                var before = character.Inventory.Bag.Items.ToDictionary(
                    item => item.Id,
                    item => item.Count);
                foreach (var line in plan.Lines)
                {
                    if (!character.Inventory.Bag.AcquireDefaultItem(
                            ItemTaskType.Invalid,
                            line.ItemId,
                            line.Count,
                            line.Grade))
                        return Reject(
                            "inventory mutation failed after validation",
                            out rejection);
                }

                character.Money -= plan.Money;
                character.HonorPoint -= (int)plan.Honor;
                character.VocationPoint -= (int)plan.Vocation;

                var tasks = new List<ItemTask>();
                foreach (var item in character.Inventory.Bag.Items)
                {
                    if (!before.TryGetValue(item.Id, out var previousCount))
                        tasks.Add(new ItemAdd(item));
                    else if (previousCount != item.Count)
                        tasks.Add(new ItemCountUpdate(item, item.Count - previousCount));
                }
                if (plan.Money > 0)
                    tasks.Add(new MoneyChange(-(int)plan.Money));

                character.SendPacket(
                    new SCItemTaskSuccessPacket(
                        ItemTaskType.StoreBuy,
                        tasks,
                        new List<ulong>()));
                if (plan.Honor > 0)
                    character.SendPacket(
                        new SCGamePointChangedPacket(
                            (byte)GamePointKind.Honor,
                            -(int)plan.Honor));
                if (plan.Vocation > 0)
                    character.SendPacket(
                        new SCGamePointChangedPacket(
                            (byte)GamePointKind.Vocation,
                            -(int)plan.Vocation));
            }
            return true;
        }

        public static bool HasCapacity(
            ItemContainer bag,
            IEnumerable<MerchantPurchaseLine> lines)
        {
            var requiredSlots = 0;
            foreach (var group in lines.GroupBy(line => (line.ItemId, line.Grade)))
            {
                var template = ItemManager.Instance.GetTemplate(group.Key.ItemId);
                if (template == null || template.MaxCount <= 0)
                    return false;
                long amount;
                try
                {
                    amount = group.Aggregate(
                        0L,
                        (total, line) => checked(total + line.Count));
                }
                catch (OverflowException)
                {
                    return false;
                }

                var existingCapacity = bag.Items
                    .Where(item =>
                        item.TemplateId == group.Key.ItemId &&
                        item.Grade == group.Key.Grade)
                    .Sum(item => Math.Max(0, template.MaxCount - item.Count));
                var remainder = Math.Max(0L, amount - existingCapacity);
                requiredSlots += (int)((remainder + template.MaxCount - 1) /
                                       template.MaxCount);
                if (requiredSlots > bag.FreeSlotCount)
                    return false;
            }
            return true;
        }

        private static int GetTemplatePrice(
            ItemTemplate template,
            ShopCurrencyType currency)
        {
            return currency switch
            {
                ShopCurrencyType.Money => template.Price,
                ShopCurrencyType.Honor => template.HonorPrice,
                ShopCurrencyType.VocationBadges => template.LivingPointPrice,
                _ => -1
            };
        }

        private static bool Reject(string reason, out string rejection)
        {
            rejection = reason;
            return false;
        }
    }
}
