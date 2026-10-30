using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Models.Game.NPChar;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxServicePolicyTests
{
    [Test]
    public async Task ChangerMustExposeTheActualNativeActionRatherThanQuestTalkOrWarehouse()
    {
        var template = new NpcTemplate { AbilityChanger = true, NonPushableByActor = true };
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "specializations", false)).IsTrue();
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "specializations", true)).IsFalse();
        template.Banker = true;
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "specializations", false)).IsFalse();
    }

    [Test]
    public async Task ShopsNeedGoodsAndServicesCannotBeAggressiveOrUnknownRoles()
    {
        var template = new NpcTemplate { Merchant = true, NonPushableByActor = true };
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "weapons", false)).IsFalse();
        template.MerchantPackId = 119;
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "weapons", false)).IsTrue();
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "armor", false)).IsTrue();
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "administrator", false)).IsFalse();
        template.Aggression = true;
        await Assert.That(MechanicsSandboxServicePolicy.SupportsRole(template, "weapons", false)).IsFalse();
    }
}
