using System;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class ArcheryBuffRemovalEventTests
    {
        [Fact]
        public void LandingAndMovementRaiseOnlyTheirNativeBuffEvent()
        {
            var owner = new Unit();
            var buff = new Buff(
                owner,
                owner,
                new SkillCasterUnit(owner.ObjId),
                new BuffTemplate { Id = 23961 },
                null,
                DateTime.UtcNow);
            var landed = 0;
            var moved = 0;
            buff.Events.OnLanding += (_, __) => landed++;
            buff.Events.OnRemoveOnMove += (_, __) => moved++;

            Buffs.RaiseRemovalEvent(buff, BuffRemoveOn.Land);
            Assert.Equal(1, landed);
            Assert.Equal(0, moved);

            Buffs.RaiseRemovalEvent(buff, BuffRemoveOn.Move);
            Assert.Equal(1, landed);
            Assert.Equal(1, moved);
        }
    }
}
