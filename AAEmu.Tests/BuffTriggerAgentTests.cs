using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class BuffTriggerAgentTests
    {
        [Fact]
        public void NativeAgentIdsResolveOwnerSourceTargetAndOriginalSource()
        {
            var owner = new Unit();
            var eventSource = new Unit();
            var eventTarget = new Unit();
            var originalSource = new Unit();

            Assert.Same(
                owner,
                BuffTrigger.ResolveAgent(0, owner, eventSource, eventTarget, originalSource));
            Assert.Same(
                eventSource,
                BuffTrigger.ResolveAgent(1, owner, eventSource, eventTarget, originalSource));
            Assert.Same(
                eventTarget,
                BuffTrigger.ResolveAgent(2, owner, eventSource, eventTarget, originalSource));
            Assert.Same(
                originalSource,
                BuffTrigger.ResolveAgent(3, owner, eventSource, eventTarget, originalSource));
            Assert.Null(
                BuffTrigger.ResolveAgent(99, owner, eventSource, eventTarget, originalSource));
        }
    }
}
