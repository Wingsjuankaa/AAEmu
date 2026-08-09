using System.Collections.Generic;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeSkillLiveTraceTests
    {
        [Fact]
        public void ArcheryAllowListMatchesTheExecutableV1Closure()
        {
            var expected = new HashSet<uint>
            {
                10694, 10708, 11368, 11933, 12133, 12759, 12792, 12793,
                12794, 13281, 14835, 14836, 14837, 15073, 15096, 16210,
                23592, 36468, 36469, 36470, 36471, 36472, 36473, 38893,
                39663, 39664, 39665, 39666, 39667, 39668, 40580, 41219,
                41221, 42849, 42851
            };

            Assert.Equal(35, ArcheryLiveTrace.TrackedSkillCount);
            foreach (var skillId in expected)
                Assert.True(ArcheryLiveTrace.IsTrackedSkill(skillId), skillId.ToString());

            Assert.False(ArcheryLiveTrace.IsTrackedSkill(2));
            Assert.False(ArcheryLiveTrace.IsTrackedSkill(39674));
        }

        [Fact]
        public void ArcheryLifecycleEventIsStableAndMachineParseable()
        {
            var line = ArcheryLiveTrace.FormatEvent(
                "effects_applied",
                36471,
                88,
                100,
                200,
                0,
                3,
                4567,
                4,
                2,
                SkillResult.Success,
                false);

            Assert.Equal(
                "[AA8ArcheryLive] phase=effects_applied skill=36471 tlId=88 caster=100 target=200 world=0 instance=3 mp=4567 targets=4 effects=2 result=Success cancelled=False",
                line);
        }

        [Fact]
        public void ArcheryPassiveAllowListAndSnapshotAreStable()
        {
            var expected = new HashSet<uint> { 2, 7, 35, 255, 256, 300 };

            Assert.Equal(6, ArcheryLiveTrace.TrackedPassiveCount);
            foreach (var passiveId in expected)
                Assert.True(ArcheryLiveTrace.IsTrackedPassive(passiveId), passiveId.ToString());

            Assert.False(ArcheryLiveTrace.IsTrackedPassive(1));
            Assert.Equal(
                "[AA8ArcheryPassive] phase=after_apply passive=255 buff=889 char=42 move=1.0800 rangedAccuracy=0.9000 rangedCritical=0.1250 rangedCriticalBonus=0.0500 rangedCriticalMul=1.5000 rangedDamageMul=1.1000 endlessDamage=110.0000 endlessRange=25.0000 concussiveCooldown=3750.0000",
                ArcheryLiveTrace.FormatPassiveSnapshot(
                    "after_apply", 255, 889, 42, 1.08, 0.9, 0.125, 0.05,
                    1.5, 1.1, 110, 25, 3750));
        }

        [Fact]
        public void DamageEventCarriesAuthoritativeHpMutation()
        {
            var line = NativeSkillLiveTrace.FormatDamageEvent(
                "archery",
                36471,
                88,
                7542,
                100,
                200,
                "Ranged",
                846,
                20,
                5000,
                4154,
                true);

            Assert.Equal(
                "[AA8SkillDamage] tree=archery skill=36471 tlId=88 effect=7542 caster=100 target=200 type=Ranged amount=846 absorbed=20 hpBefore=5000 hpAfter=4154 packet=True",
                line);
        }

        [Fact]
        public void PeriodicDamageTraceRecoversTheOriginatingSkillFromCastBuff()
        {
            var skill = new Skill(new SkillTemplate { Id = 41478 });
            var buff = new Buff(null, null, null, new BuffTemplate { Id = 24585 }, skill,
                System.DateTime.UtcNow);

            var resolved = NativeSkillLiveTrace.ResolveOriginSkill(
                null,
                new CastBuff(buff));

            Assert.Same(skill, resolved);
            Assert.Equal((uint)41478, resolved.Id);
        }

        [Fact]
        public void DirectDamageSkillTakesPrecedenceOverCastBuffMetadata()
        {
            var direct = new Skill(new SkillTemplate { Id = 39674 });
            var periodic = new Skill(new SkillTemplate { Id = 41478 });
            var buff = new Buff(null, null, null, new BuffTemplate { Id = 24585 }, periodic,
                System.DateTime.UtcNow);

            var resolved = NativeSkillLiveTrace.ResolveOriginSkill(
                direct,
                new CastBuff(buff));

            Assert.Same(direct, resolved);
        }
    }
}
