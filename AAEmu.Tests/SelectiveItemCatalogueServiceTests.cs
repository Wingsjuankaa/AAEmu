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
                43476,
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
                    43476,
                    new SelectiveItemOption { Index = 1, ResultItemId = 43490 }));
        }

        [Fact]
        public void ReusedSkillIsAmbiguousButBothSourcesRemainResolvable()
        {
            var service = new SelectiveItemCatalogueService();
            service.RegisterAction(
                new SelectiveItemAction { SkillId = 42205, SourceItemId = 47868 });
            service.RegisterAction(
                new SelectiveItemAction { SkillId = 42205, SourceItemId = 48061 });

            Assert.False(service.TryGetBySkill(42205, out _));
            Assert.True(service.TryGetBySourceItem(47868, out var first));
            Assert.True(service.TryGetBySourceItem(48061, out var second));
            Assert.NotSame(first, second);
        }
    }
}
