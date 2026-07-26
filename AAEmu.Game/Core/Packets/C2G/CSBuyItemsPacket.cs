using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Merchant;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSBuyItemsPacket : GamePacket
    {
        public CSBuyItemsPacket() : base(CSOffsets.CSBuyItemsPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var npcObjId = stream.ReadBc();
            var npc = WorldManager.Instance.GetNpc(npcObjId);
            var doodadObjId = stream.ReadBc();
            var doodad = WorldManager.Instance.GetDoodad(doodadObjId);
            var unkId = stream.ReadUInt32();
            var nBuy = stream.ReadByte();
            var nBuyBack = stream.ReadByte();

            _log.Debug(
                "NPCObjId:{0} DoodadObjId:{1} unkId:{2} nBuy:{3} nBuyBack:{4}",
                npcObjId,
                doodadObjId,
                unkId,
                nBuy,
                nBuyBack);

            var requests = new List<MerchantPurchaseRequest>(nBuy);
            for (var index = 0; index < nBuy; index++)
            {
                requests.Add(
                    new MerchantPurchaseRequest
                    {
                        ItemId = stream.ReadUInt32(),
                        Grade = stream.ReadByte(),
                        Count = stream.ReadInt32(),
                        Currency = (ShopCurrencyType)stream.ReadByte()
                    });
            }

            var buyBackIndices = new List<int>(nBuyBack);
            for (var index = 0; index < nBuyBack; index++)
                buyBackIndices.Add(stream.ReadInt32());
            _ = stream.ReadBoolean(); // useAAPoint; not a merchant price authority.

            var character = Connection.ActiveChar;
            if (character == null)
                return;
            if (nBuy > 0 && nBuyBack > 0)
            {
                Reject("mixed purchases and buyback are not atomic");
                return;
            }

            if (nBuyBack > 0)
            {
                TryCommitBuyBack(buyBackIndices);
                return;
            }

            if (nBuy == 0)
            {
                Reject("empty purchase");
                return;
            }
            if (npcObjId == 0 ||
                npc == null ||
                !npc.Template.Merchant ||
                npc.Template.MerchantPackId == 0)
            {
                Reject("purchase has no valid authoritative NPC merchant");
                return;
            }
            if (doodadObjId != 0)
            {
                // AA8 doodad stores need their own native stock relation. They
                // must not fall through to client-selected item/price data.
                Reject("doodad merchant stock is not closed");
                return;
            }

            var distance = MathUtil.CalculateDistance(
                character.Transform.World.Position,
                npc.Transform.World.Position);
            if (distance > 3f)
            {
                character.SendErrorMessage(ErrorMessageType.TooFarAway);
                return;
            }

            var stock = NpcManager.Instance.GetGoods(npc.Template.MerchantPackId);
            var service = MerchantPurchaseService.Instance;
            if (!service.TryPrepare(
                    character,
                    stock,
                    requests,
                    out var plan,
                    out var rejection))
            {
                Reject(rejection);
                return;
            }
            if (!service.TryCommit(character, plan, out rejection))
            {
                Reject(rejection);
                return;
            }

            _log.Info(
                "AA8 merchant purchase committed: character={0}, npc={1}, " +
                "pack={2}, lines={3}, money={4}, honor={5}, vocation={6}",
                character.Name,
                npc.TemplateId,
                npc.Template.MerchantPackId,
                plan.Lines.Count,
                plan.Money,
                plan.Honor,
                plan.Vocation);
        }

        private void TryCommitBuyBack(IReadOnlyCollection<int> indices)
        {
            var character = Connection.ActiveChar;
            if (indices.Count == 0 || indices.Distinct().Count() != indices.Count)
            {
                Reject("invalid or repeated buyback index");
                return;
            }

            var entries = new List<Item>();
            long total = 0;
            try
            {
                foreach (var index in indices)
                {
                    var item = character.BuyBackItems.GetItemBySlot(index);
                    var grade = item == null
                        ? null
                        : ItemManager.Instance.GetGradeTemplate(item.Grade);
                    if (item == null || grade == null)
                    {
                        Reject($"unknown buyback index {index}");
                        return;
                    }
                    var unit = checked(
                        (long)(item.Template.Refund * grade.RefundMultiplier / 100f));
                    total = checked(total + unit * item.Count);
                    entries.Add(item);
                }
            }
            catch (OverflowException)
            {
                Reject("buyback total overflow");
                return;
            }

            if (total > int.MaxValue || total > character.Money)
            {
                Reject("insufficient money for buyback");
                return;
            }
            if (character.Inventory.Bag.FreeSlotCount < entries.Count)
            {
                character.SendErrorMessage(ErrorMessageType.BagFull);
                return;
            }

            lock (character.Inventory.Bag)
            {
                if (total > character.Money ||
                    character.Inventory.Bag.FreeSlotCount < entries.Count)
                {
                    Reject("buyback state changed before commit");
                    return;
                }

                var tasks = new List<ItemTask>();
                foreach (var item in entries)
                {
                    if (!character.Inventory.Bag.AddOrMoveExistingItem(
                            ItemTaskType.Invalid,
                            item))
                    {
                        Reject("buyback inventory mutation failed");
                        return;
                    }
                    tasks.Add(new ItemBuyback(item));
                }
                character.Money -= total;
                if (total > 0)
                    tasks.Add(new MoneyChange(-(int)total));
                character.SendPacket(
                    new SCItemTaskSuccessPacket(
                        ItemTaskType.StoreBuy,
                        tasks,
                        new List<ulong>()));
            }
        }

        private void Reject(string reason)
        {
            _log.Warn(
                "AA8 merchant purchase rejected for {0}: {1}",
                Connection.ActiveChar?.Name ?? "<disconnected>",
                reason);
            Connection.ActiveChar?.Inventory.SendAuthoritativeContainer(
                SlotType.Inventory);
        }
    }
}
