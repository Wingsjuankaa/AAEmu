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

        private static List<Buff> GetEffects(Buffs buffs)
        {
            var field = typeof(Buffs).GetField("_effects", BindingFlags.Instance | BindingFlags.NonPublic);
            return Assert.IsType<List<Buff>>(field?.GetValue(buffs));
        }
    }
}
