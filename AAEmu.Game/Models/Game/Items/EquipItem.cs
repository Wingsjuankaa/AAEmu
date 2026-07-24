using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items
{
    public class EquipItem : Item
    {
        // Kakao 8.0 x2game.dll FUN_396c0d40 exposes detail +0x08 as
        // "gemInfo", and the nine contiguous values at +0x18..+0x38 as
        // "socketInfo". In the server's packet-order array those fields are
        // GemIds[1] and GemIds[4..12], respectively.
        public const int EnchantingGemIndex = 1;
        public const int NativeSocketStartIndex = 4;
        public const int NativeSocketCapacity = 9;

        public override ItemDetailType DetailType => ItemDetailType.Equipment;

        public virtual int Str => 0;
        public virtual int Dex => 0;
        public virtual int Sta => 0;
        public virtual int Int => 0;
        public virtual int Spi => 0;
        public virtual byte MaxDurability => 0;

        public uint EnchantingGemItemId
        {
            get => GemIds[EnchantingGemIndex];
            set
            {
                GemIds[EnchantingGemIndex] = value;
                IsDirty = true;
            }
        }

        public int OccupiedNativeSocketCount
        {
            get
            {
                var occupied = 0;
                for (var index = 0; index < NativeSocketCapacity; index++)
                {
                    if (GemIds[NativeSocketStartIndex + index] != 0)
                        occupied++;
                }

                return occupied;
            }
        }

        public bool TryGetFirstEmptyNativeSocket(int maximumSockets, out int gemArrayIndex)
        {
            var limit = Math.Min(
                Math.Max(maximumSockets, 0),
                NativeSocketCapacity);
            for (var index = 0; index < limit; index++)
            {
                var candidate = NativeSocketStartIndex + index;
                if (GemIds[candidate] != 0)
                    continue;

                gemArrayIndex = candidate;
                return true;
            }

            gemArrayIndex = -1;
            return false;
        }

        public bool SetNativeSocket(int socketIndex, uint itemId)
        {
            if (socketIndex < 0 || socketIndex >= NativeSocketCapacity)
                return false;

            GemIds[NativeSocketStartIndex + socketIndex] = itemId;
            IsDirty = true;
            return true;
        }

        public int RepairCost
        {
            get
            {
                var template = (EquipItemTemplate)Template;
                var grade = ItemManager.Instance.GetGradeTemplate(Grade);
                var cost = ItemManager.Instance.GetDurabilityRepairCostFactor() * 0.0099999998f *
                           (1f - Durability * 1f / MaxDurability) * template.Price;
                cost = cost * grade.RefundMultiplier * 0.0099999998f;
                cost = (float)Math.Ceiling(cost);
                if (cost < 0 || cost < int.MinValue || cost > int.MaxValue)
                    cost = 0;
                return (int)cost;
            }
        }

        public EquipItem()
        {
            GemIds = new uint[18];
        }

        public EquipItem(ulong id, ItemTemplate template, int count) : base(id, template, count)
        {
            GemIds = new uint[18];
        }
    }
}
