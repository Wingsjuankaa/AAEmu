using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Models.Game.Merchant
{
    /// <summary>
    /// Identifies actorless character-panel stores without trusting their
    /// client-selected item list. The open type and currency only select a
    /// server-owned stock pack loaded from the compact database.
    /// </summary>
    public static class GlobalMerchantPurchasePolicy
    {
        public static bool TryGetLookupCurrency(
            uint npcObjId,
            uint doodadObjId,
            uint unknownId,
            bool useAaPoint,
            byte openType,
            int buyBackCount,
            IEnumerable<MerchantPurchaseRequest> requests,
            out ShopCurrencyType currency)
        {
            currency = default;
            if (npcObjId != 0 ||
                doodadObjId != 0 ||
                unknownId != 0 ||
                useAaPoint ||
                openType == 0 ||
                buyBackCount != 0 ||
                requests == null)
                return false;

            var currencies = requests
                .Where(request => request != null)
                .Select(request => request.Currency)
                .Distinct()
                .Take(2)
                .ToArray();
            if (currencies.Length != 1)
                return false;

            currency = currencies[0];
            return true;
        }
    }
}
