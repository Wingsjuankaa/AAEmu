using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemSocketRuleServiceTests
{
    [Test]
    public async Task FirstInstall_UsesSocketOneAndHonorsNativeLimit()
    {
        var service = NewService(firstInstallChance: 10000, maximumSockets: 2);
        var (target, reagent) = NewItems();

        var first = service.Validate(target, reagent);
        await Assert.That(first.IsValid).IsTrue();
        await Assert.That(first.SuccessChance).IsEqualTo(10000);
        await Assert.That(first.MaximumSockets).IsEqualTo(2);

        target.SetNativeSocket(0, reagent.TemplateId);
        target.SetNativeSocket(1, reagent.TemplateId);
        var full = service.Validate(target, reagent);
        await Assert.That(full.Failure).IsEqualTo(ItemSocketValidationFailure.SocketsFull);
    }

    [Test]
    public async Task ZeroProbability_FailsClosedInsteadOfBecomingGuaranteed()
    {
        var service = NewService(firstInstallChance: 0, maximumSockets: 2);
        var (target, reagent) = NewItems();

        var validation = service.Validate(target, reagent);

        await Assert.That(validation.Failure)
            .IsEqualTo(ItemSocketValidationFailure.ProbabilityUnavailable);
    }

    [Test]
    public async Task SlotOutsideNativeGroup_IsRejected()
    {
        var service = NewService(firstInstallChance: 10000, maximumSockets: 2);
        var (target, reagent) = NewItems();
        ((WeaponTemplate)target.Template).HoldableTemplate.SlotTypeId = 99;

        var validation = service.Validate(target, reagent);

        await Assert.That(validation.Failure).IsEqualTo(ItemSocketValidationFailure.SlotMismatch);
    }

    private static ItemSocketRuleService NewService(int firstInstallChance, int maximumSockets)
    {
        var service = new ItemSocketRuleService();
        service.RegisterDefinition(new ItemSocketDefinition
        {
            Id = 1,
            ItemId = 43500,
            EquipSlotGroupId = 38,
            ItemSocketChanceId = 7,
            IgnoreEquipItemTag = true
        });
        var chance = new ItemSocketChanceDefinition { Id = 7, CostRatio = 100 };
        chance.SocketChances[0] = 0; // native sentinel, never the first install chance
        chance.SocketChances[1] = firstInstallChance;
        chance.SocketChances[2] = 10000;
        service.RegisterChance(chance);
        service.RegisterSlotGroupMember(38, 4);
        service.RegisterSocketLimit(4, 12, maximumSockets);
        service.MarkNativeCatalogueAvailable();
        return service;
    }

    private static (EquipItem Target, Item Reagent) NewItems()
    {
        var targetTemplate = new WeaponTemplate
        {
            Id = 60000,
            Level = 55,
            HoldableTemplate = new Holdable { SlotTypeId = 4 }
        };
        var target = new EquipItem(1, targetTemplate, 1) { Grade = 12 };
        var reagentTemplate = new ItemTemplate { Id = 43500, Level = 1 };
        var reagent = new Item(2, reagentTemplate, 1);
        return (target, reagent);
    }
}
