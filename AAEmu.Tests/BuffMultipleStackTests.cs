using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class BuffMultipleStackTests
    {
        [Fact]
        public void MultipleInstancesPublishTheirNativeStackDepth()
        {
            var owner = new Unit();
            var buffs = new Buffs(owner);
            var flags = BindingFlags.Instance | BindingFlags.NonPublic;
            var buffTagsField = typeof(SkillManager).GetField("_buffTags", flags);
            var buffTriggersField = typeof(SkillManager).GetField("_buffTriggers", flags);
            var originalBuffTags = buffTagsField?.GetValue(SkillManager.Instance);
            var originalBuffTriggers = buffTriggersField?.GetValue(SkillManager.Instance);
            var template = new BuffTemplate
            {
                Id = 0,
                StackRule = BuffStackRule.Multiple,
                MaxStack = 3
            };

            Assert.NotNull(buffTagsField);
            Assert.NotNull(buffTriggersField);
            buffTagsField.SetValue(SkillManager.Instance, new Dictionary<uint, List<uint>>());
            buffTriggersField.SetValue(
                SkillManager.Instance,
                new Dictionary<uint, List<BuffTriggerTemplate>>());
            try
            {
                for (var expectedStack = 1; expectedStack <= template.MaxStack; expectedStack++)
                {
                    buffs.AddBuff(new Buff(
                        owner,
                        owner,
                        new SkillCasterUnit(owner.ObjId),
                        template,
                        null,
                        DateTime.UtcNow));

                    Assert.Equal(expectedStack, GetEffects(buffs).Last().Stack);
                }

                Assert.Equal(3, buffs.GetBuffCountById(template.Id));
            }
            finally
            {
                buffTagsField.SetValue(SkillManager.Instance, originalBuffTags);
                buffTriggersField.SetValue(SkillManager.Instance, originalBuffTriggers);
            }
        }

        [Fact]
        public void NativeBuffGroupSelectsOnlyDistinctActiveMembers()
        {
            var owner = new Unit();
            var stageOne = new Buff(
                owner,
                owner,
                new SkillCasterUnit(owner.ObjId),
                new BuffTemplate { Id = 242, GroupId = 10, GroupRank = 1 },
                null,
                DateTime.UtcNow);
            var sameStage = new Buff(
                owner,
                owner,
                new SkillCasterUnit(owner.ObjId),
                stageOne.Template,
                null,
                DateTime.UtcNow);
            stageOne.InUse = true;
            sameStage.InUse = true;

            var incoming = new BuffTemplate { Id = 514, GroupId = 10, GroupRank = 2 };
            var members = Buffs.GetActiveGroupMembers(
                incoming,
                new[] { stageOne, sameStage }).ToList();

            Assert.Equal(2, members.Count);
            Assert.Empty(Buffs.GetActiveGroupMembers(stageOne.Template, new[] { stageOne, sameStage }));
            Assert.Empty(Buffs.GetActiveGroupMembers(
                new BuffTemplate { Id = 999, GroupId = 0, GroupRank = 99 },
                new[] { stageOne }));
        }

        private static List<Buff> GetEffects(Buffs buffs)
        {
            var field = typeof(Buffs).GetField("_effects", BindingFlags.Instance | BindingFlags.NonPublic);
            return Assert.IsType<List<Buff>>(field?.GetValue(buffs));
        }
    }
}
