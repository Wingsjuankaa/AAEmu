using System;

using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils.Scripts;

using Xunit;

namespace AAEmu.Tests
{
    public class GmSpeedLevelPolicyTests
    {
        [Theory]
        [InlineData(1, 10, 1.01f)]
        [InlineData(50, 500, 1.50f)]
        [InlineData(100, 1000, 2.00f)]
        public void LevelsMapToNativeMoveSpeedModifier(
            int level,
            ushort expectedAbilityLevel,
            float expectedMultiplier)
        {
            var abilityLevel = GmSpeedLevelPolicy.ToNativeAbilityLevel(level);
            var unit = new Unit();

            unit.AddBonus(1, new Bonus
            {
                Template = new BonusTemplate
                {
                    Attribute = UnitAttribute.MoveSpeedMul,
                    ModifierType = UnitModifierType.Value
                },
                Value = abilityLevel
            });

            Assert.Equal(expectedAbilityLevel, abilityLevel);
            Assert.InRange(unit.MoveSpeedMul, expectedMultiplier - 0.0001f, expectedMultiplier + 0.0001f);
            Assert.InRange(
                GmSpeedLevelPolicy.ToMoveSpeedMultiplier(level),
                expectedMultiplier - 0.0001f,
                expectedMultiplier + 0.0001f);
        }

        [Theory]
        [InlineData(0)]
        [InlineData(101)]
        [InlineData(-1)]
        public void OutOfRangeLevelsAreRejected(int level)
        {
            Assert.False(GmSpeedLevelPolicy.IsValid(level));
            Assert.Throws<ArgumentOutOfRangeException>(
                () => GmSpeedLevelPolicy.ToNativeAbilityLevel(level));
        }

        [Fact]
        public void SpeedCommandCompilesInTheRuntimeScriptAssembly()
        {
            Assert.True(ScriptCompiler.CompileScripts(out var assembly));
            Assert.NotNull(assembly);
            Assert.NotNull(assembly.GetType("AAEmu.Game.Scripts.Commands.Speed"));
        }
    }
}
