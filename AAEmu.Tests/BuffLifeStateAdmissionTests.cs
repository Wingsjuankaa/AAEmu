using System;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class BuffLifeStateAdmissionTests
    {
        [Fact]
        public void DeadUnitRejectsBuffThatIsNotDeadApplicable()
        {
            var owner = new Unit {Hp = 0};
            var caster = new Unit {Hp = 100};
            var template = new BuffTemplate
            {
                Id = 2214,
                DeadApplicable = false
            };
            var effect = new BuffEffect
            {
                Chance = 100,
                Buff = template
            };

            effect.Apply(caster, null, owner, null, null, null, null, DateTime.UtcNow);

            Assert.Equal(0, owner.Buffs.GetBuffCountById(template.Id));
        }
    }
}
