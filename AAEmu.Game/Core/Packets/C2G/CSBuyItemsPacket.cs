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
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Core.Packets.C2G
{
    public sealed class MerchantPurchasePacketData
    {
        public const byte MaximumLineCount = 16;

        public uint NpcObjId { get; internal set; }
        public uint DoodadObjId { get; internal set; }
        public uint UnknownId { get; internal set; }
        public IReadOnlyList<MerchantPurchaseRequest> Requests { get; internal set; }
        public IReadOnlyList<int> BuyBackIndices { get; internal set; }
        public bool UseAaPoint { get; internal set; }
        public byte OpenType { get; internal set; }

        public static MerchantPurchasePacketData Read(PacketStream stream)
        {
            var npcObjId = stream.ReadBc();
            var doodadObjId = stream.ReadBc();
            var unknownId = stream.ReadUInt32();
            var purchaseCount = stream.ReadByte();
            var buyBackCount = stream.ReadByte();

            // Both AA8 native serializers clamp these fixed arrays to 16.
            // Reject an invalid wire count instead of reading beyond their
            // authoritative packet layout.
            if (purchaseCount > MaximumLineCount ||
                buyBackCount > MaximumLineCount)
                throw new MarshalException();

            var requests = new List<MerchantPurchaseRequest>(purchaseCount);
            for (var index = 0; index < purchaseCount; index++)
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

            var buyBackIndices = new List<int>(buyBackCount);
            for (var index = 0; index < buyBackCount; index++)
                buyBackIndices.Add(stream.ReadInt32());

            var useAaPoint = stream.ReadBoolean();
            var openType = stream.ReadByte();
            if (stream.HasBytes)
                throw new MarshalException();

            return new MerchantPurchasePacketData
            {
                NpcObjId = npcObjId,
                DoodadObjId = doodadObjId,
                UnknownId = unknownId,
                Requests = requests,
                BuyBackIndices = buyBackIndices,
                UseAaPoint = useAaPoint,
                OpenType = openType
            };
        }
    }

    public class CSBuyItemsPacket : GamePacket
    {
        public CSBuyItemsPacket() : base(CSOffsets.CSBuyItemsPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var data = MerchantPurchasePacketData.Read(stream);
            var npcObjId = data.NpcObjId;
            var npc = WorldManager.Instance.GetNpc(npcObjId);
            var doodadObjId = data.DoodadObjId;
            var doodad = WorldManager.Instance.GetDoodad(doodadObjId);
            var nBuy = data.Requests.Count;
            var nBuyBack = data.BuyBackIndices.Count;
            var npcMerchantPackId = npc?.Template?.MerchantPackId ?? 0;
            var stock = npcMerchantPackId == 0
                ? null
                : NpcManager.Instance.GetGoods(npcMerchantPackId);

            _log.Debug(
                "NPCObjId:{0} DoodadObjId:{1} unkId:{2} nBuy:{3} " +
                "nBuyBack:{4} useAAPoint:{5} openType:{6}",
                npcObjId,
                doodadObjId,
                data.UnknownId,
                nBuy,
                nBuyBack,
                data.UseAaPoint,
                data.OpenType);

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
                TryCommitBuyBack(data.BuyBackIndices);
                return;
            }

            if (nBuy == 0)
            {
                Reject("empty purchase");
                return;
            }

            var isGlobalPurchase =
                GlobalMerchantPurchasePolicy.TryGetLookupCurrency(
                    npcObjId,
                    doodadObjId,
                    data.UnknownId,
                    data.UseAaPoint,
                    data.OpenType,
                    nBuyBack,
                    data.Requests,
                    out var globalCurrency);
            if (isGlobalPurchase)
                stock = NpcManager.Instance.GetGlobalGoods(
                    data.OpenType,
                    globalCurrency);

            if (isGlobalPurchase && stock == null)
            {
                CaptureRejectedPurchase(
                    data,
                    npc,
                    doodad,
                    stock,
                    "merchant_context_validation",
                    $"global merchant openType {data.OpenType} currency " +
                    $"{globalCurrency} has no authoritative stock");
                Reject(
                    $"global merchant openType {data.OpenType} currency " +
                    $"{globalCurrency} has no authoritative stock");
                return;
            }
            if (!isGlobalPurchase &&
                (npcObjId == 0 ||
                 npc == null ||
                 !npc.Template.Merchant ||
                 npc.Template.MerchantPackId == 0))
            {
                CaptureRejectedPurchase(
                    data,
                    npc,
                    doodad,
                    stock,
                    "merchant_context_validation",
                    "purchase has no valid authoritative NPC merchant");
                Reject("purchase has no valid authoritative NPC merchant");
                return;
            }
            if (!isGlobalPurchase && doodadObjId != 0)
            {
                // AA8 doodad stores need their own native stock relation. They
                // must not fall through to client-selected item/price data.
                CaptureRejectedPurchase(
                    data,
                    npc,
                    doodad,
                    stock,
                    "merchant_context_validation",
                    "doodad merchant stock is not closed");
                Reject("doodad merchant stock is not closed");
                return;
            }

            if (!isGlobalPurchase)
            {
                var distance = MathUtil.CalculateDistance(
                    character.Transform.World.Position,
                    npc.Transform.World.Position);
                if (distance > 3f)
                {
                    character.SendErrorMessage(ErrorMessageType.TooFarAway);
                    return;
                }
            }

            var service = MerchantPurchaseService.Instance;
            if (!service.TryPrepare(
                    character,
                    stock,
                    data.Requests,
                    out var plan,
                    out var rejection))
            {
                CaptureRejectedPurchase(
                    data,
                    npc,
                    doodad,
                    stock,
                    "prepare",
                    rejection);
                Reject(rejection);
                return;
            }
            if (!service.TryCommit(character, plan, out rejection))
            {
                CaptureRejectedPurchase(
                    data,
                    npc,
                    doodad,
                    stock,
                    "commit",
                    rejection);
                Reject(rejection);
                return;
            }

            _log.Info(
                "AA8 merchant purchase committed: character={0}, context={1}, " +
                "npc={2}, pack={3}, lines={4}, money={5}, honor={6}, vocation={7}",
                character.Name,
                isGlobalPurchase ? $"global:{data.OpenType}" : "npc",
                npc?.TemplateId ?? 0,
                stock.Id,
                plan.Lines.Count,
                plan.Money,
                plan.Honor,
                plan.Vocation);
        }

        private void CaptureRejectedPurchase(
            MerchantPurchasePacketData data,
            Npc npc,
            Doodad doodad,
            MerchantGoods stock,
            string failureStage,
            string failureReason)
        {
            var character = Connection.ActiveChar;
            MerchantPurchaseCaptureService.Instance.CaptureRejectedBatch(
                new MerchantPurchaseCaptureBatch
                {
                    FailureStage = failureStage,
                    FailureReason = failureReason,
                    CharacterId = character?.Id ?? 0,
                    CharacterName = character?.Name,
                    NpcObjId = data.NpcObjId,
                    NpcTemplateId = npc?.TemplateId ?? 0,
                    NpcName = npc?.Template?.Name,
                    NpcMerchantFlag = npc?.Template?.Merchant ?? false,
                    MerchantPackId = npc?.Template?.MerchantPackId ?? stock?.Id ?? 0,
                    DoodadObjId = data.DoodadObjId,
                    DoodadTemplateId = doodad?.TemplateId ?? 0,
                    UnknownId = data.UnknownId,
                    UseAaPoint = data.UseAaPoint,
                    OpenType = data.OpenType,
                    Stock = stock,
                    Requests = data.Requests
                });
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
