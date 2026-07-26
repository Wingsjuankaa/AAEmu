using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Models.Game.Merchant
{
    public class MerchantGoods
    {
        public uint Id { get; set; }
        public List<MerchantGoodsItem> Items { get; set; }

        public MerchantGoods(uint id)
        {
            Id = id;
            Items = new List<MerchantGoodsItem>();
        }

        public bool SellsItem(uint itemTemplateId)
        {
            return Items.Any(item => item.ItemTemplateId == itemTemplateId);
        }

        public MerchantGoodsItem GetStock(
            uint itemTemplateId,
            byte itemGrade,
            ShopCurrencyType currency)
        {
            return Items.FirstOrDefault(
                item => item.ItemTemplateId == itemTemplateId &&
                        item.Grade == itemGrade &&
                        item.Currency == currency);
        }

        public void AddItemToStock(
            uint itemTemplateId,
            byte itemGrade,
            ShopCurrencyType currency = ShopCurrencyType.Money,
            int price = -1)
        {
            if (GetStock(itemTemplateId, itemGrade, currency) != null)
                return;
            Items.Add(
                new MerchantGoodsItem
                {
                    ItemTemplateId = itemTemplateId,
                    Grade = itemGrade,
                    Currency = currency,
                    Price = price
                });
        }
    }

    public class MerchantGoodsItem
    {
        public uint ItemTemplateId;
        public byte Grade;
        public ShopCurrencyType Currency;

        // A non-negative value is an authoritative pack override. A negative
        // value means that the native pack delegates to the item template.
        public int Price = -1;
    }
}
