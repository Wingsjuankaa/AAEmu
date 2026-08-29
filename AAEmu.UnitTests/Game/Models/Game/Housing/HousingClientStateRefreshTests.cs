using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.UnitTests.Game.Models.Game.Housing;

public class HousingClientStateRefreshTests
{
    [Test]
    public async Task RemodelingRefresh_InvalidatesOldAgentBeforeRecreatingRelogState()
    {
        var template = new HousingTemplate
        {
            Id = 434,
            MainModelId = 900,
            HousingBindings = []
        };
        template.BuildSteps.Add(0, new HousingBuildStep
        {
            HousingId = template.Id,
            Step = 0,
            ModelId = 800,
            SkillId = 29291,
            NumActions = 1
        });
        var house = new House
        {
            Template = template,
            TemplateId = template.Id,
            Id = 16,
            ObjId = 271,
            TlId = 7,
            Name = "Thatched Farmhouse",
            CurrentStep = 0,
            NumAction = 0
        };

        var packets = HousingClientStateRefresh.BuildPackets(house);

        var expectedOrder = new[]
        {
            typeof(SCUnitsRemovedPacket),
            typeof(SCUnitStatePacket),
            typeof(SCHouseStatePacket),
            typeof(SCHouseDataPacket),
            typeof(SCHouseBuildProgressPacket)
        };
        await Assert.That(packets.Select(packet => packet.GetType()).SequenceEqual(expectedOrder)).IsTrue();

        var expectedRemoval = new PacketStream();
        new SCUnitsRemovedPacket([house.ObjId]).Write(expectedRemoval);
        var actualRemoval = new PacketStream();
        packets[0].Write(actualRemoval);
        await Assert.That(actualRemoval.GetBytes().SequenceEqual(expectedRemoval.GetBytes())).IsTrue();

        var expectedHouseState = new PacketStream();
        house.Write(expectedHouseState);
        var refreshedHouseState = new PacketStream();
        packets[2].Write(refreshedHouseState);
        await Assert.That(refreshedHouseState.GetBytes().SequenceEqual(expectedHouseState.GetBytes())).IsTrue();
        await Assert.That(house.CurrentStep).IsEqualTo(0);
        await Assert.That(house.ModelId).IsEqualTo(800u);
    }

    [Test]
    public async Task RemodelingRefresh_RestoresFactionAfterFreshUnitState()
    {
        var house = new House
        {
            Template = new HousingTemplate
            {
                Id = 432,
                MainModelId = 1774,
                HousingBindings = []
            },
            TemplateId = 432,
            ObjId = 271,
            TlId = 18,
            Name = "Thatched Farmhouse",
            CurrentStep = -1,
            Faction = new SystemFaction { Id = FactionsEnum.NuiaAlliance }
        };

        var packets = HousingClientStateRefresh.BuildPackets(house);

        var expectedOrder = new[]
        {
            typeof(SCUnitsRemovedPacket),
            typeof(SCUnitStatePacket),
            typeof(SCHouseStatePacket),
            typeof(SCUnitFactionChangedPacket),
            typeof(SCHouseDataPacket),
            typeof(SCHouseBuildProgressPacket)
        };
        await Assert.That(packets.Select(packet => packet.GetType()).SequenceEqual(expectedOrder)).IsTrue();
    }

    [Test]
    public async Task RemodelingRefresh_RecreatesSurvivingChildrenAfterParentWithoutMutatingHouse()
    {
        var house = new House
        {
            Template = new HousingTemplate
            {
                Id = 432,
                MainModelId = 1774,
                HousingBindings = []
            },
            TemplateId = 432,
            ObjId = 271,
            TlId = 18,
            CurrentStep = -1
        };
        house.AttachedDoodads.Add(new Doodad { ObjId = 9001 });

        var first = HousingClientStateRefresh.BuildPackets(house);
        var second = HousingClientStateRefresh.BuildPackets(house);

        var expectedOrder = new[]
        {
            typeof(SCUnitsRemovedPacket),
            typeof(SCUnitStatePacket),
            typeof(SCHouseStatePacket),
            typeof(SCDoodadsCreatedPacket),
            typeof(SCHouseDataPacket),
            typeof(SCHouseBuildProgressPacket)
        };
        await Assert.That(first.Select(packet => packet.GetType()).SequenceEqual(expectedOrder)).IsTrue();
        await Assert.That(second.Select(packet => packet.GetType()).SequenceEqual(expectedOrder)).IsTrue();
        await Assert.That(house.ObjId).IsEqualTo(271u);
        await Assert.That(house.TemplateId).IsEqualTo(432u);
        await Assert.That(house.CurrentStep).IsEqualTo(-1);
        await Assert.That(house.AttachedDoodads).Count().IsEqualTo(1);
    }
}
