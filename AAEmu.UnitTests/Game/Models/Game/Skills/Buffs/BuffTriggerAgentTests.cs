using AAEmu.Game.Models.Game.Skills.Buffs;
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

        await Assert.That(BuffTriggerAgentRules.Pick((BuffTriggerAgent)0, owner, originalSource, eventSource, eventTarget))
            .IsSameReferenceAs(owner);
        await Assert.That(BuffTriggerAgentRules.Pick((BuffTriggerAgent)1, owner, originalSource, eventSource, eventTarget))
            .IsSameReferenceAs(eventSource);
        await Assert.That(BuffTriggerAgentRules.Pick((BuffTriggerAgent)2, owner, originalSource, eventSource, eventTarget))
            .IsSameReferenceAs(eventTarget);
        await Assert.That(BuffTriggerAgentRules.Pick((BuffTriggerAgent)3, owner, originalSource, eventSource, eventTarget))
            .IsSameReferenceAs(originalSource);
        await Assert.That(BuffTriggerAgentRules.Pick((BuffTriggerAgent)99, owner, originalSource, eventSource, eventTarget))
            .IsNull();
    }
}
