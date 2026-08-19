using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Trading;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCSpecialtyPacketsTests
{
    [Test]
    public async Task RatioPacket_WritesNativeR575HeaderAndCurrentBackpackQuote()
    {
        var quote = new SpecialtyQuote
        {
            ItemId = 31_856,
            Refund = 100_001,
            NoEventRefund = 80_001,
            Ratio = 130,
            Stock = 4,
            CanProduce = true,
            Currency = ShopCurrencyType.Money,
            Type = 0
        };
        var stream = new PacketStream();

        new SCSpecialtyRatioPacket(5, 17_971, [quote], [], true, true).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)5);
        await Assert.That(body.ReadUInt32()).IsEqualTo(17_971u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadBoolean()).IsTrue();
        var decoded = body.Read<SpecialtyQuote>();
        await Assert.That(decoded).IsEqualTo(quote);
        await Assert.That(body.HasBytes).IsFalse();
    }

    [Test]
    public async Task GoodsPacket_RejectsMoreThanNativeTwentyQuotes()
    {
        var quotes = Enumerable.Range(1, 21)
            .Select(id => new SpecialtyQuote { ItemId = (uint)id })
            .ToList();

        var write = () => new SCSpecialtyGoodsPacket(quotes, [], true, true).Write(new PacketStream());

        await Assert.That(write).Throws<ArgumentOutOfRangeException>();
    }
}
