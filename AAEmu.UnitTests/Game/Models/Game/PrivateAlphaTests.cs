using System.Text;
using AAEmu.Game.Models.Game.PrivateAlpha;

namespace AAEmu.UnitTests.Game.Models.Game;

public class PrivateAlphaTests
{
    [Test]
    public async Task PointGrantsRejectInvalidOrOverflowingAmountsWithoutPartialDelivery()
    {
        foreach (var amount in new[] { int.MinValue, -1, 0, 100001, int.MaxValue })
        {
            await Assert.That(AlphaRules.TryPoints(50, amount, out var next)).IsFalse();
            await Assert.That(next).IsEqualTo(50);
        }
        await Assert.That(AlphaRules.TryPoints(int.MaxValue - 5, 6, out var overflow)).IsFalse();
        await Assert.That(overflow).IsEqualTo(int.MaxValue - 5);
        await Assert.That(AlphaRules.TryPoints(-1, 1, out _)).IsFalse();
        await Assert.That(AlphaRules.TryPoints(50, 100000, out var granted)).IsTrue();
        await Assert.That(granted).IsEqualTo(100050);
        await Assert.That(AlphaRules.TryPoints(int.MaxValue - 1, 1, out var edge)).IsTrue();
        await Assert.That(edge).IsEqualTo(int.MaxValue);
    }

    [Test]
    public async Task AccessRequiresFeatureAndEntitlementWithoutDependingOnInventory()
    {
        for (var bits = 0; bits < 4; bits++)
            await Assert.That(AlphaRules.CanUse((bits & 1) != 0, (bits & 2) != 0)).IsEqualTo(bits == 3);
        await Assert.That(AlphaRules.CreateKey().Sellable).IsFalse();
        await Assert.That(AlphaRules.CreateKey().UseSkillId).IsEqualTo(0u);
        await Assert.That(AlphaRules.CreateKey().MaxCount).IsEqualTo(1);
    }

    [Test]
    public async Task GoldRejectsInvalidAmountsAndOverflowWithoutChangingTheBalance()
    {
        foreach (var amount in new[] { -1, 0, 10001, int.MaxValue })
        {
            await Assert.That(AlphaRules.TryGold(123, amount, 10000, out var result)).IsFalse();
            await Assert.That(result).IsEqualTo(123L);
        }
        await Assert.That(AlphaRules.TryGold(long.MaxValue - 1, 1, 10000, out _)).IsFalse();
        await Assert.That(AlphaRules.TryGold(123, 1000, 10000, out var next)).IsTrue();
        await Assert.That(next).IsEqualTo(10000123L);
        await Assert.That(AlphaRules.StacksNeeded(1000, 999)).IsEqualTo(2);
        await Assert.That(AlphaRules.StacksNeeded(int.MaxValue, int.MaxValue)).IsEqualTo(1);
        await Assert.That(AlphaRules.StacksNeeded(1, 0)).IsEqualTo(int.MaxValue);
    }

    [Test]
    public async Task SearchKeepsUtf8AndNormalizesSpanishDiacritics()
    {
        var text = "Infusión de síntesis";
        await Assert.That(AlphaTransport.DecodeQuery(Convert.ToHexString(Encoding.UTF8.GetBytes(text)))).IsEqualTo(text);
        await Assert.That(AlphaRules.Normalize(text)).IsEqualTo("infusion de sintesis");
        foreach (var spelling in new[] { "Jarrón", "JARRÓN", "JARRON", "Jarro\u0301n" })
            await Assert.That(AlphaRules.Normalize(spelling)).IsEqualTo("jarron");
        await Assert.That(AlphaRules.Normalize("ÁÉÍÓÚÜÑ áéíóúüñ")).IsEqualTo("aeiouun aeiouun");
        await Assert.That(AlphaRules.Normalize("Decorative Vase 98")).IsEqualTo("decorative vase 98");
        foreach (var bad in new[] { "f", "zz", "ffff", new string('a', 194) })
            await Assert.That(AlphaTransport.DecodeQuery(bad)).IsNull();
        await Assert.That(AlphaTransport.DecodeQuery("")).IsEqualTo("");
    }

    [Test]
    public async Task TransportRequiresOrderedCompleteFramesAndRejectsReplay()
    {
        var transport = new AlphaTransport(); var now = DateTime.UtcNow;
        var a = "aa10ap1:ab:1:2:" + new string('x', 24);
        var b = "aa10ap1:ab:2:2:tail";
        await Assert.That(transport.Receive(b, "", false, now, out _)).IsNull();
        await Assert.That(transport.Receive(a, "", false, now, out _)).IsNull();
        await Assert.That(transport.Receive(b, "", false, now, out var id)).IsEqualTo(new string('x', 24) + "tail");
        await Assert.That(id).IsEqualTo(171u);
        await Assert.That(transport.Receive(a, "", false, now.AddHours(1), out _)).IsNull();
        await Assert.That(transport.Receive(b, "", false, now.AddHours(1), out _)).IsNull();
    }

    [Test]
    public async Task TransportRejectsExpiredOversizedAndForgedChannelFrames()
    {
        var now = DateTime.UtcNow;
        foreach (var frame in new[] { "aa10ap1:0:1:1:open", "aa10ap1:1:0:1:open", "aa10ap1:1:1:13:open", "aa10ap1:1:1:2:short", "aa10ap1:1:1:1:" + new string('x', 25), "aa10ap1:1:1:1:ñ" })
            await Assert.That(new AlphaTransport().Receive(frame, "", false, now, out _)).IsNull();
        await Assert.That(new AlphaTransport().Receive("aa10ap1:1:1:1:open", "secret", false, now, out _)).IsNull();
        await Assert.That(new AlphaTransport().Receive("aa10ap1:1:1:1:open", "", true, now, out _)).IsNull();
        var transport = new AlphaTransport();
        transport.Receive("aa10ap1:1:1:2:" + new string('x', 24), "", false, now, out _);
        await Assert.That(transport.Receive("aa10ap1:1:2:2:tail", "", false, now.AddSeconds(6), out _)).IsNull();
    }
}
