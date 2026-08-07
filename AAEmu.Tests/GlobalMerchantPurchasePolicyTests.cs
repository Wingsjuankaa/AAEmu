using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Merchant;

using Xunit;

namespace AAEmu.Tests
{
    public class GlobalMerchantPurchasePolicyTests
    {
        private static readonly IReadOnlyList<MerchantPurchaseRequest> HonorRequests =
            new[]
            {
                new MerchantPurchaseRequest
                {
                    ItemId = 45732,
                    Grade = 3,
                    Count = 1,
                    Currency = ShopCurrencyType.Honor
                }
            };

        [Fact]
        public void AcceptsObservedActorlessHonorStoreContext()
        {
            var accepted = GlobalMerchantPurchasePolicy.TryGetLookupCurrency(
                0, 0, 0, false, 2, 0, HonorRequests, out var currency);

            Assert.True(accepted);
            Assert.Equal(ShopCurrencyType.Honor, currency);
        }

        [Theory]
        [InlineData(1u, 0u, 0u, false, (byte)2, 0)]
        [InlineData(0u, 1u, 0u, false, (byte)2, 0)]
        [InlineData(0u, 0u, 1u, false, (byte)2, 0)]
        [InlineData(0u, 0u, 0u, true, (byte)2, 0)]
        [InlineData(0u, 0u, 0u, false, (byte)0, 0)]
        [InlineData(0u, 0u, 0u, false, (byte)2, 1)]
        public void RejectsContextsOutsideTheObservedGlobalContract(
            uint npcObjId,
            uint doodadObjId,
            uint unknownId,
            bool useAaPoint,
            byte openType,
            int buyBackCount)
        {
            Assert.False(
                GlobalMerchantPurchasePolicy.TryGetLookupCurrency(
                    npcObjId,
                    doodadObjId,
                    unknownId,
                    useAaPoint,
                    openType,
                    buyBackCount,
                    HonorRequests,
                    out _));
        }

        [Fact]
        public void RejectsMixedClientCurrencies()
        {
            var mixed = new List<MerchantPurchaseRequest>(HonorRequests)
            {
                new MerchantPurchaseRequest
                {
                    ItemId = 45732,
                    Grade = 3,
                    Count = 1,
                    Currency = ShopCurrencyType.Money
                }
            };

            Assert.False(
                GlobalMerchantPurchasePolicy.TryGetLookupCurrency(
                    0, 0, 0, false, 2, 0, mixed, out _));
        }
    }
}
