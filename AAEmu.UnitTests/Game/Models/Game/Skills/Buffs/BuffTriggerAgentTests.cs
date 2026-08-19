using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Buffs;

public class BuffTriggerAgentTests
{
    [Test]
    public async Task NativeAgentIdsResolveOwnerEventAndOriginalSource()
    {
        var owner = new Unit();
        var eventSource = new Unit();
        var eventTarget = new Unit();
        var originalSource = new Unit();

        await Assert.That(BuffTrigger.ResolveAgent(0, owner, eventSource, eventTarget, originalSource))
            .IsSameReferenceAs(owner);
        await Assert.That(BuffTrigger.ResolveAgent(1, owner, eventSource, eventTarget, originalSource))
            .IsSameReferenceAs(eventSource);
        await Assert.That(BuffTrigger.ResolveAgent(2, owner, eventSource, eventTarget, originalSource))
            .IsSameReferenceAs(eventTarget);
        await Assert.That(BuffTrigger.ResolveAgent(3, owner, eventSource, eventTarget, originalSource))
            .IsSameReferenceAs(originalSource);
        await Assert.That(BuffTrigger.ResolveAgent(99, owner, eventSource, eventTarget, originalSource))
            .IsNull();
    }
}
