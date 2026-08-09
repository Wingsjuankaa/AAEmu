using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Game.Skills;

using Xunit;

namespace AAEmu.Tests
{
    public class AreaTriggerBuffTagTests
    {
        [Fact]
        public void RequiredDuskMarkerLimitsStealthToMarkedCaster()
        {
            const uint duskMarkerTag = 4176;
            Assert.True(AreaTrigger.PassesBuffTagFilter(duskMarkerTag, true, 0, false));
            Assert.False(AreaTrigger.PassesBuffTagFilter(duskMarkerTag, false, 0, false));
        }

        [Fact]
        public void ExcludedTagRejectsOtherwiseEligibleUnit()
        {
            const uint excludedTag = 451;
            Assert.False(AreaTrigger.PassesBuffTagFilter(0, false, excludedTag, true));
            Assert.True(AreaTrigger.PassesBuffTagFilter(0, false, excludedTag, false));
        }

        [Fact]
        public void NativeCloutUseOriginSourceCarriesSkillAndTimeline()
        {
            var skill = new Skill { Id = 41478, TlId = 39896 };
            var trigger = new AreaTrigger
            {
                SkillId = skill.Id,
                TlId = skill.TlId,
                OriginSkill = AreaTrigger.SelectOriginSkill(true, skill)
            };

            Assert.Same(skill, trigger.OriginSkill);
            Assert.Same(skill, trigger.CreateEffectSource().Skill);

            var cast = Assert.IsType<CastSkill>(trigger.CreateCastAction());
            Assert.Equal(skill.Id, cast.SkillId);
            Assert.Equal(skill.TlId, cast.TlId);
        }

        [Fact]
        public void NativeCloutWithoutUseOriginSourceDoesNotLeakSkillContext()
        {
            var skill = new Skill { Id = 41478, TlId = 39896 };

            Assert.Null(AreaTrigger.SelectOriginSkill(false, skill));
        }
    }
}
