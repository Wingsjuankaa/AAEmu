using AAEmu.Game.Models.Game.Items.Services;

using Xunit;

namespace AAEmu.Tests
{
    public class SelectiveItemCatalogueServiceTests
    {
        [Fact]
        public void ClosedActionResolvesBySkillAndSourceItem()
        {
            var service = new SelectiveItemCatalogueService();
            var action = new SelectiveItemAction
            {
                SkillId = 36944,
                SourceItemId = 43476,
                SelectCount = 1,
                ConsumeItemCount = 1,
                IsMulti = true
            };
            service.RegisterAction(action);
            service.RegisterOption(
                36944,
                new SelectiveItemOption
                {
                    Index = 1,
                    ResultItemId = 43490,
                    Count = 1,
                    ResultUid = "54100655"
                });

            Assert.True(service.NativeCatalogueAvailable);
            Assert.True(service.TryGetBySkill(36944, out var bySkill));
            Assert.True(service.TryGetBySourceItem(43476, out var bySource));
            Assert.Same(bySkill, bySource);
            Assert.Equal((uint)43490, bySkill.Options[1].ResultItemId);
        }

        [Fact]
        public void UnknownSourceDoesNotFallback()
        {
            var service = new SelectiveItemCatalogueService();

            Assert.False(service.TryGetBySourceItem(43476, out _));
            Assert.False(service.NativeCatalogueAvailable);
        }

        [Fact]
        public void OptionCannotReferenceMissingAction()
        {
            var service = new SelectiveItemCatalogueService();

            Assert.Throws<System.InvalidOperationException>(
                () => service.RegisterOption(
                    36944,
                    new SelectiveItemOption { Index = 1, ResultItemId = 43490 }));
        }
    }
}
