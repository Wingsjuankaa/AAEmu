using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Merchant;

using Xunit;

namespace AAEmu.Tests
{
    public class MerchantPurchaseServiceTests
    {
        [Fact]
        public void StockResolutionRequiresExactGradeAndCurrency()
        {
            var stock = new MerchantGoods(145);
            stock.AddItemToStock(48845, 2, ShopCurrencyType.Money, 100);

            Assert.NotNull(stock.GetStock(48845, 2, ShopCurrencyType.Money));
            Assert.Null(stock.GetStock(48845, 3, ShopCurrencyType.Money));
            Assert.Null(stock.GetStock(48845, 2, ShopCurrencyType.Honor));
        }

        [Fact]
        public void SameItemCanHaveMultipleAuthoritativeStockPolicies()
        {
            var stock = new MerchantGoods(145);
            stock.AddItemToStock(48845, 2, ShopCurrencyType.Money, 100);
            stock.AddItemToStock(48845, 3, ShopCurrencyType.Money, 200);
            stock.AddItemToStock(48845, 2, ShopCurrencyType.Honor, 10);

            Assert.Equal(3, stock.Items.Count);
            Assert.Equal(
                200,
                stock.GetStock(48845, 3, ShopCurrencyType.Money).Price);
        }

        [Fact]
        public void TotalsRejectInvalidQuantityAndUnsupportedCurrency()
        {
            Assert.False(
                MerchantPurchaseService.TryCalculateTotals(
                    new[]
                    {
                        new MerchantPurchaseLine
                        {
                            Count = 0,
                            UnitPrice = 10,
                            Currency = ShopCurrencyType.Money
                        }
                    },
                    out _,
                    out _,
                    out _,
                    out _));
            Assert.False(
                MerchantPurchaseService.TryCalculateTotals(
                    new[]
                    {
                        new MerchantPurchaseLine
                        {
                            Count = 1,
                            UnitPrice = 10,
                            Currency = ShopCurrencyType.SiegeShop
                        }
                    },
                    out _,
                    out _,
                    out _,
                    out _));
        }

        [Fact]
        public void TotalsKeepAllRequiredCurrenciesIndependent()
        {
            var lines = new List<MerchantPurchaseLine>
            {
                new MerchantPurchaseLine
                {
                    Count = 2,
                    UnitPrice = 100,
                    Currency = ShopCurrencyType.Money
                },
                new MerchantPurchaseLine
                {
                    Count = 3,
                    UnitPrice = 10,
                    Currency = ShopCurrencyType.Honor
                },
                new MerchantPurchaseLine
                {
                    Count = 4,
                    UnitPrice = 5,
                    Currency = ShopCurrencyType.VocationBadges
                }
            };

            Assert.True(
                MerchantPurchaseService.TryCalculateTotals(
                    lines,
                    out var money,
                    out var honor,
                    out var vocation,
                    out _));
            Assert.Equal(200, money);
            Assert.Equal(30, honor);
            Assert.Equal(20, vocation);
        }
    }
}
