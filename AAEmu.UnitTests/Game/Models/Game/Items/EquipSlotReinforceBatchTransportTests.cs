using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class EquipSlotReinforceBatchTransportTests
{
    private static readonly DateTime Now = new(2026,9,6,23,0,0,DateTimeKind.Utc);
    private const string Payload="1,17,7,0,2450,490/12:2/11:4";
    private static string[] Frames(string payload,uint id=1)
    {
        var count=(payload.Length+22)/23;
        return Enumerable.Range(0,count).Select(i=>$"aa10ip3:{id}:{i+1}:{count}:{payload.Substring(i*23,Math.Min(23,payload.Length-i*23))}").ToArray();
    }

    [Test]
    public async Task CompleteNativeSizedFramesAuthorizeExactlyOnce()
    {
        var transport=new EquipSlotReinforceBatchTransport();
        var frames=Frames(Payload);
        for(var i=0;i<frames.Length;i++)
        {
            await Assert.That(frames[i].Length<=48).IsTrue();
            var request=transport.Receive(frames[i],"",false,Now,out var cancelled);
            await Assert.That(cancelled).IsEqualTo(0u);
            if(i+1==frames.Length) await Assert.That(request?.GainExperience).IsEqualTo(2450);
            else await Assert.That(request).IsNull();
        }
        foreach(var frame in frames) await Assert.That(transport.Receive(frame,"",false,Now,out _)).IsNull();
    }

    [Test]
    public async Task MissingExpiredCancelledOrInconsistentFragmentsCannotStartACast()
    {
        var frames=Frames(Payload);
        var transport=new EquipSlotReinforceBatchTransport();
        await Assert.That(transport.Receive(frames[1],"",false,Now,out _)).IsNull();
        transport.Receive(frames[0],"",false,Now,out _);
        await Assert.That(transport.Receive(frames[1],"",false,Now.AddSeconds(6),out _)).IsNull();
        transport=new(); transport.Receive(frames[0],"",false,Now,out _);
        transport.Receive("aa10ip3cancel:1","",false,Now,out var cancelled);
        await Assert.That(cancelled).IsEqualTo(1u);
        await Assert.That(transport.Receive(frames[1],"",false,Now,out _)).IsNull();
        transport=new(); transport.Receive(frames[0],"",false,Now,out _);
        await Assert.That(transport.Receive(frames[0][..^1]+"9","",false,Now,out _)).IsNull();
        await Assert.That(transport.Receive(frames[1],"",false,Now,out _)).IsNull();
    }

    [Test]
    public async Task ChannelsAndConnectionsCannotMixQuotesOrBypassEnvelopeLimits()
    {
        var a=new EquipSlotReinforceBatchTransport(); var b=new EquipSlotReinforceBatchTransport();
        var frames=Frames(Payload);
        a.Receive(frames[0],"",false,Now,out _);
        await Assert.That(b.Receive(frames[1],"",false,Now,out _)).IsNull();
        foreach(var frame in new[]{"ordinary channel","aa10ip3:1:0:2:a","aa10ip3:1:1:999:a",new string('a',49),"aa10ip3:0:1:1:a"})
            await Assert.That(a.Receive(frame,"",false,Now,out _)).IsNull();
        foreach(var frame in frames)
        {
            await Assert.That(b.Receive(frame,"password",false,Now,out _)).IsNull();
            await Assert.That(b.Receive(frame,"",true,Now,out _)).IsNull();
        }
        // Envelope request ID and quoted request ID must agree.
        foreach(var frame in Frames(Payload,2)) await Assert.That(b.Receive(frame,"",false,Now,out _)).IsNull();
    }
}
