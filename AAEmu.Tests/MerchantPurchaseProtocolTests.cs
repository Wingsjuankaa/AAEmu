using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Items;

using Xunit;

namespace AAEmu.Tests
{
    public class MerchantPurchaseProtocolTests
    {
        [Fact]
        public void KakaoAa8PurchasePacketUsesObservedOpcodeAndLayout()
        {
            var packet = new CSBuyItemsPacket();

            Assert.Equal((ushort)0x0F0, packet.TypeId);
            Assert.Equal((byte)5, packet.Level);

            var observed = new byte[]
            {
                0xb9, 0x90, 0x00,
                0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00,
                0x01,
                0x00,
                0xfc, 0xba, 0x00, 0x00,
                0x00,
                0x01, 0x00, 0x00, 0x00,
                0x00,
                0x00,
                0x00
            };

            var data = MerchantPurchasePacketData.Read(new PacketStream(observed));

            Assert.Equal((uint)37049, data.NpcObjId);
            Assert.Equal((uint)0, data.DoodadObjId);
            Assert.Equal((uint)0, data.UnknownId);
            Assert.Single(data.Requests);
            Assert.Equal((uint)47868, data.Requests[0].ItemId);
            Assert.Equal((byte)0, data.Requests[0].Grade);
            Assert.Equal(1, data.Requests[0].Count);
            Assert.Equal(ShopCurrencyType.Money, data.Requests[0].Currency);
            Assert.Empty(data.BuyBackIndices);
            Assert.False(data.UseAaPoint);
            Assert.Equal((byte)0, data.OpenType);
        }

        [Fact]
        public void ParserSupportsMultiplePurchaseLinesAndOpenType()
        {
            var wire = new PacketStream()
                .WriteBc(37049)
                .WriteBc(0)
                .Write((uint)77)
                .Write((byte)2)
                .Write((byte)0)
                .Write((uint)47868)
                .Write((byte)0)
                .Write(1)
                .Write((byte)ShopCurrencyType.Money)
                .Write((uint)47869)
                .Write((byte)2)
                .Write(3)
                .Write((byte)ShopCurrencyType.Honor)
                .Write(true)
                .Write((byte)4);

            var data = MerchantPurchasePacketData.Read(
                new PacketStream(wire.GetBytes()));

            Assert.Equal(2, data.Requests.Count);
            Assert.Equal((uint)47869, data.Requests[1].ItemId);
            Assert.Equal((byte)2, data.Requests[1].Grade);
            Assert.Equal(3, data.Requests[1].Count);
            Assert.Equal(ShopCurrencyType.Honor, data.Requests[1].Currency);
            Assert.True(data.UseAaPoint);
            Assert.Equal((byte)4, data.OpenType);
        }

        [Fact]
        public void ParserSupportsBuyBackIndices()
        {
            var wire = new PacketStream()
                .WriteBc(37049)
                .WriteBc(0)
                .Write((uint)0)
                .Write((byte)0)
                .Write((byte)2)
                .Write(3)
                .Write(7)
                .Write(false)
                .Write((byte)1);

            var data = MerchantPurchasePacketData.Read(
                new PacketStream(wire.GetBytes()));

            Assert.Empty(data.Requests);
            Assert.Equal(new[] { 3, 7 }, data.BuyBackIndices);
            Assert.False(data.UseAaPoint);
            Assert.Equal((byte)1, data.OpenType);
        }

        [Fact]
        public void ParserRejectsCountsBeyondNativeFixedArrays()
        {
            var wire = new PacketStream()
                .WriteBc(37049)
                .WriteBc(0)
                .Write((uint)0)
                .Write((byte)17)
                .Write((byte)0);

            Assert.Throws<MarshalException>(
                () => MerchantPurchasePacketData.Read(
                    new PacketStream(wire.GetBytes())));
        }
    }
}
