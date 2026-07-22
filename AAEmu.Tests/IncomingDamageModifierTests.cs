using System;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Xunit;

namespace AAEmu.Tests
{
    public class IncomingDamageModifierTests
    {
        [Fact]
        public void EarthEnergyAppliesAndRemovesThirtyPercentIncomingDamageReduction()
        {
            // Kakao 8.0 compact source of truth:
            // buff 2596 -> UnitAttribute 58 (IncomingDamageMul), value -300.
            var character = new Character(new UnitCustomModelParams());
            var template = new BuffTemplate { Id = 2596 };
            template.Bonuses.Add(new BonusTemplate
            {
                Attribute = UnitAttribute.IncomingDamageMul,
                ModifierType = UnitModifierType.Value,
                Value = -300,
                LinearLevelBonus = 0
            });

            var buff = new Buff(
                character,
                character,
                new SkillCasterUnit(character.ObjId),
                template,
                null,
                DateTime.UtcNow)
            {
                Index = 2596,
                AbLevel = 1,
                Passive = true
            };

            template.Start(character, character, buff);

            Assert.Equal(0.7f, character.IncomingDamageMul, 3);
            Assert.Equal(0.7f, character.IncomingMeleeDamageMul, 3);
            Assert.Equal(0.7f, character.IncomingRangedDamageMul, 3);
            Assert.Equal(0.7f, character.IncomingSpellDamageMul, 3);
            Assert.Equal(44, (int)(63 * character.IncomingSpellDamageMul));

            template.Dispel(character, character, buff);

            Assert.Equal(1.0f, character.IncomingDamageMul, 3);
            Assert.Equal(1.0f, character.IncomingMeleeDamageMul, 3);
            Assert.Equal(1.0f, character.IncomingRangedDamageMul, 3);
            Assert.Equal(1.0f, character.IncomingSpellDamageMul, 3);
        }
    }
}
