using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillLaborSettlementTests
{
    [Test]
    public async Task LaborBearingSkill_GrantsVocationOnlyAfterSuccessfulPayment()
    {
        await Assert.That(Skill.CanGrantVocation(false, 10, false)).IsFalse();
        await Assert.That(Skill.CanGrantVocation(false, 10, true)).IsTrue();
    }

    [Test]
    public async Task ExplicitZeroCostSkill_CanKeepAuthoredVocationReward()
    {
        await Assert.That(Skill.CanGrantVocation(false, 0, false)).IsTrue();
        await Assert.That(Skill.CanGrantVocation(true, 0, true)).IsFalse();
    }
}
