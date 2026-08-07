using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class StealthDetectionTests
    {
        [Fact]
        public void NativeMinusOneThousandModifierDisablesStealthDetectionRange()
        {
            var observer = new Unit();
            observer.AddBonus(1, new Bonus
            {
                Template = new BonusTemplate
                {
                    Attribute = UnitAttribute.DetectStealthRangeMul,
                    ModifierType = UnitModifierType.Value
                },
                Value = -1000
            });

            Assert.Equal(0f, observer.DetectStealthRangeMul);
        }

        [Fact]
        public void NpcCannotDetectStealthedTargetWhenDetectionRangeIsZero()
        {
            Assert.False(Npc.IsWithinDetectionRange(1f, 10f, true, 0f));
            Assert.True(Npc.IsWithinDetectionRange(1f, 10f, false, 0f));
            Assert.True(Npc.IsWithinDetectionRange(4f, 10f, true, 0.5f));
            Assert.False(Npc.IsWithinDetectionRange(6f, 10f, true, 0.5f));
        }

        [Fact]
        public void DetectionMultiplierDefaultsToOne()
        {
            Assert.Equal(1f, new Unit().DetectStealthRangeMul);
        }
    }
}
