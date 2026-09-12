using System.Text;
using AAEmu.Game.Models.Game.BugReports;

namespace AAEmu.UnitTests.Game.Models.Game;

public class BugReportTests
{
    [Test]
    public async Task HistoryChunksRoundTripSpanishAndMaximumUnicodeWithoutLeakingMetadata()
    {
        var detail = "¿Dónde?\n" + string.Concat(Enumerable.Repeat("😀", 590));
        var chunks = BugReportHistory.DetailChunks(detail).ToArray();
        await Assert.That(chunks.All(c => c.Length <= 240)).IsTrue();
        await Assert.That(Encoding.UTF8.GetString(Convert.FromHexString(string.Concat(chunks)))).IsEqualTo(detail);
        var summary = BugReportHistory.Summary(new(3, new DateTime(2026,9,11,23,39,0), "new", "quest", 10029, "¿Dónde está Gladie?", detail));
        await Assert.That(summary.StartsWith("3/new/2026-09-11 23:39/quest/10029/", StringComparison.Ordinal)).IsTrue();
        await Assert.That(summary.Contains(detail, StringComparison.Ordinal)).IsFalse();
    }

    [Test]
    public async Task DetailAndEntityValidationIsStrictButAllowsSpanishAndNewlines()
    {
        const string detail = "La misión no avanza.\nEsperaba completar el objetivo.";
        await Assert.That(BugReportRules.Valid("quest", 10022, "abcd-1234", detail)).IsTrue();
        foreach (var category in new[] { "world", "ui", "other" })
        {
            await Assert.That(BugReportRules.Valid(category, 0, "abcd-1234", detail)).IsTrue();
            await Assert.That(BugReportRules.Valid(category, 1, "abcd-1234", detail)).IsFalse();
        }
        foreach (var invalid in new[] { "", "     ", "short", new string('x',601), "bad\0details here" })
            await Assert.That(BugReportRules.Valid("item", 98, "abcd-1234", invalid)).IsFalse();
        await Assert.That(BugReportRules.Valid("quest",0,"abcd-1234",detail)).IsFalse();
        await Assert.That(BugReportRules.Valid("admin",1,"abcd-1234",detail)).IsFalse();
        await Assert.That(BugReportRules.Valid("item",98,"sql';--",detail)).IsFalse();
        await Assert.That(BugReportRules.Decode("c328",2400)).IsNull();
        await Assert.That(BugReportRules.Decode(Convert.ToHexString(Encoding.UTF8.GetBytes(detail)),2400)).IsEqualTo(detail);
        await Assert.That(BugReportRules.Valid("ui",0,"abcd-1234",string.Concat(Enumerable.Repeat("😀",600)))).IsTrue();
    }

    [Test]
    public async Task LongReportReassemblesOnceAndRejectsDuplicatesAndOutOfOrder()
    {
        var text = "submit/quest/10022/abcd-1234/" + Convert.ToHexString(Encoding.UTF8.GetBytes(new string('á',600)));
        var parts = Enumerable.Range(0,(text.Length+19)/20).Select(i=>text.Substring(i*20,Math.Min(20,text.Length-i*20))).ToArray();
        var t=new BugReportTransport(); var now=DateTime.UtcNow; string received=null;
        for(var i=0;i<parts.Length;i++)
        {
            var frame=$"aa10br1:7fffffff:{i+1}:{parts.Length}:{parts[i]}";
            await Assert.That(frame.Length<=48).IsTrue();
            received=t.Receive(frame,"",false,now,out var id);
            if(i<parts.Length-1) await Assert.That(received).IsNull();
            else await Assert.That(id).IsEqualTo(0x7fffffffu);
        }
        await Assert.That(received).IsEqualTo(text);
        await Assert.That(t.Receive($"aa10br1:7fffffff:1:{parts.Length}:{parts[0]}","",false,now,out _)).IsNull();
        var broken=new BugReportTransport();
        await Assert.That(broken.Receive("aa10br1:2:1:2:"+new string('a',20),"",false,now,out _)).IsNull();
        await Assert.That(broken.Receive("aa10br1:2:2:2:b","",false,now.AddSeconds(31),out _)).IsNull();
        await Assert.That(broken.Receive("aa10br1:3:2:2:b","",false,now,out _)).IsNull();
        await Assert.That(broken.Receive("aa10br1:4:1:1:open","password",false,now,out _)).IsNull();
        await Assert.That(broken.Receive("aa10br1:5:1:1:open","",true,now,out _)).IsNull();
        await Assert.That(broken.Receive("aa10br1:6:1:261:"+new string('a',20),"",false,now,out _)).IsNull();
    }

    [Test]
    public async Task FingerprintGroupsSameEntityAndDetailWithoutMergingDifferentEntities()
    {
        await Assert.That(BugReportRules.Fingerprint("item",98,"JARRÓN falla")).IsEqualTo(BugReportRules.Fingerprint("item",98,"jarron falla"));
        await Assert.That(BugReportRules.Fingerprint("item",98,"jarron falla")).IsNotEqualTo(BugReportRules.Fingerprint("item",99,"jarron falla"));
    }
}
