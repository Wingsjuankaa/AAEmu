using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class ItemEnchantScaleServiceTests
    {
        [Theory]
        [InlineData(10, 1.01)]
        [InlineData(100, 1.10)]
        [InlineData(250, 1.25)]
        public void NativeScaleUsesPermilleAboveBase(int scale, double expected)
        {
            var service = new ItemEnchantScaleService();
            service.MarkNativeCatalogueAvailable();
            service.Register(new EnchantScaleRatio
            {
                Id = 1,
                Scale = scale
            });

            Assert.Equal(expected, service.GetMultiplier(1), 5);
        }

        [Fact]
        public void ScaledAZeroKeepsBaseStats()
        {
            var service = new ItemEnchantScaleService();
            service.MarkNativeCatalogueAvailable();

            Assert.Equal(1d, service.GetMultiplier(0));
        }

        [Fact]
        public void NativeForbidListOverridesItemCap()
        {
            var service = new ItemEnchantScaleService();
            service.MarkNativeCatalogueAvailable();
            service.RegisterForbiddenItem(1000);
            var item = new Weapon
            {
                TemplateId = 1000,
                Template = new WeaponTemplate { Id = 1000, MaxEnchantScaleId = 30 }
            };

            Assert.False(service.CanTemper(item));
        }

        [Fact]
        public void EquipmentWithNativeCapCanBeTempered()
        {
            var service = new ItemEnchantScaleService();
            service.MarkNativeCatalogueAvailable();
            var item = new Weapon
            {
                TemplateId = 1000,
                Template = new WeaponTemplate { Id = 1000, MaxEnchantScaleId = 30 }
            };

            Assert.True(service.CanTemper(item));
        }

        [Fact]
        public void NativeProbabilityNormalizationMatchesX2GameThresholds()
        {
            var ratio = new EnchantScaleRatio
            {
                SuccessRatio = 3000,
                GreatSuccessRatio = 2000,
                BreakRatio = 0,
                DisableRatio = 0,
                DownRatio = 5000
            };

            var result =
                ItemEnchantScaleService.NormalizeProbabilities(ratio, null, true);

            Assert.Equal(3000, result.SuccessThreshold);
            // x2game performs this multiplication in float and truncates.
            Assert.Equal(599, result.GreatSuccessRatio);
            Assert.Equal(3500, result.DowngradeRatio);
            Assert.Equal(3500, result.FailRatio);
            Assert.Equal(6500, result.DowngradeThreshold);
        }

        [Fact]
        public void NormalCatalystCannotProduceGreatSuccess()
        {
            var ratio = new EnchantScaleRatio
            {
                SuccessRatio = 10000,
                GreatSuccessRatio = 2000
            };

            var result =
                ItemEnchantScaleService.NormalizeProbabilities(ratio, null, false);

            Assert.Equal(0, result.GreatSuccessRatio);
        }

        [Fact]
        public void NativeSupportUsesImplementationBitAndScaleRange()
        {
            var service = CompleteService();
            service.RegisterSupport(new ItemGradeEnchantingSupportDefinition
            {
                ItemId = 48858,
                ImplementationFlags = 2,
                RequiredScaleMinId = 2,
                RequiredScaleMaxId = 30,
                AddSuccessMultiplier = 50
            });
            var item = TemperableWeapon(2);

            Assert.True(
                service.TryCreateAttempt(
                    item, (int)TemperTargetKind.Weapon, false, 48858,
                    out var attempt, out var failure),
                failure);
            Assert.NotNull(attempt.Support);
            Assert.Equal(10000, attempt.Probabilities.SuccessRatio);

            Assert.False(
                service.TryCreateAttempt(
                    item, (int)TemperTargetKind.Armor, false, 48858,
                    out _, out _));
        }

        [Fact]
        public void ShiningCatalystUsesNativeGreatSuccessStep()
        {
            var service = CompleteService();
            var item = TemperableWeapon(10);
            Assert.True(
                service.TryCreateAttempt(
                    item, (int)TemperTargetKind.Weapon, true, 0,
                    out var attempt, out var failure),
                failure);

            var outcome = service.ResolveOutcome(attempt, 0, 1);

            Assert.Equal(ItemRefurbishmentResult.GreatSuccess, outcome.Result);
            Assert.Equal((ushort)12, outcome.AfterScaleId);
        }

        [Fact]
        public void HistoricalZeroScaleIsRejectedUntilNativeInitialization()
        {
            var service = CompleteService();
            var item = TemperableWeapon(0);

            Assert.False(
                service.TryCreateAttempt(
                    item, (int)TemperTargetKind.Weapon, false, 0,
                    out _, out var failure));
            Assert.Contains("initialized", failure);
        }

        [Fact]
        public void ScaledAMarksItemDirtyForPersistence()
        {
            var item = TemperableWeapon(1);
            item.IsDirty = false;

            item.ScaledA = 2;

            Assert.True(item.IsDirty);
        }

        private static ItemEnchantScaleService CompleteService()
        {
            var service = new ItemEnchantScaleService();
            for (ushort id = 1; id <= 31; id++)
            {
                service.Register(new EnchantScaleRatio
                {
                    Id = id,
                    Scale = id == 31 ? 250 : id * 10,
                    SuccessRatio = id < 30 ? 10000 : 0,
                    GreatSuccessRatio = id < 29 ? 2000 : 0,
                    DownMax = 1
                });
            }
            service.MarkNativeCatalogueAvailable();
            return service;
        }

        private static Weapon TemperableWeapon(ushort scale)
        {
            return new Weapon
            {
                TemplateId = 1000,
                Template = new WeaponTemplate
                {
                    Id = 1000,
                    MaxEnchantScaleId = 30
                },
                ScaledA = scale
            };
        }
    }
}
