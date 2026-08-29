using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSStartInteractionPacketTests
{
    [Test]
    public async Task ActiveHouseBuildStepReturnsItsAa10Skill()
    {
        var template = new HousingTemplate { Id = 437 };
        template.BuildSteps.Add(0, new HousingBuildStep
        {
            HousingId = 437,
            Step = 0,
            SkillId = 29291,
            NumActions = 1
        });
        var house = new House { Template = template, TemplateId = 437 };
        house.CurrentStep = 0;

        await Assert.That(CSStartInteractionPacket.GetActiveHouseBuildSkillId(house))
            .IsEqualTo(29291u);
    }

    [Test]
    public async Task CompletedOrUnknownHouseBuildStepReturnsNoSkill()
    {
        var template = new HousingTemplate { Id = 437 };
        template.BuildSteps.Add(0, new HousingBuildStep
        {
            HousingId = 437,
            Step = 0,
            SkillId = 29291,
            NumActions = 1
        });
        var house = new House { Template = template, TemplateId = 437 };
        house.CurrentStep = -1;

        await Assert.That(CSStartInteractionPacket.GetActiveHouseBuildSkillId(house)).IsEqualTo(0u);
    }
}
