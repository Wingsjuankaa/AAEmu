using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Skills.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class ChargeCooldownSpecialEffectTests
    {
        [Fact]
        public void Aa8SpecialType158MapsToChargeCooldown()
        {
            Assert.Equal(158, (int)SpecialType.ChargeCooldown);
            Assert.Equal(nameof(ChargeCooldown), SpecialType.ChargeCooldown.ToString());
        }

        [Fact]
        public void SkillTemplatePreservesNativeChargeContract()
        {
            var template = new SkillTemplate
            {
                ChargeCount = 5,
                ChargeCooldownTime = 22000
            };

            Assert.Equal(5, template.ChargeCount);
            Assert.Equal(22000, template.ChargeCooldownTime);
        }
    }
}
