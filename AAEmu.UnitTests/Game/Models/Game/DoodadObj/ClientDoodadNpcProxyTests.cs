using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class ClientDoodadNpcProxyTests
{
    [Test]
    public async Task GetFuncGroupId_ClientNpcProxy_PrefersNormalNpcModel()
    {
        var doodad = CreateDoodad(
            clientDoodad: true,
            new DoodadFuncGroups
            {
                Id = 41495,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                Model = "invalid_model"
            },
            new DoodadFuncGroups
            {
                Id = 41496,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                Model = "npctype://10581"
            });

        await Assert.That(doodad.GetFuncGroupId()).IsEqualTo(41496u);
    }

    [Test]
    public async Task GetFuncGroupId_ClientNpcProxy_FallsBackToStartNpcModel()
    {
        var doodad = CreateDoodad(
            clientDoodad: true,
            new DoodadFuncGroups
            {
                Id = 700,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                Model = "npctype://42"
            });

        await Assert.That(doodad.GetFuncGroupId()).IsEqualTo(700u);
    }

    [Test]
    public async Task GetFuncGroupId_OrdinaryDoodad_KeepsStartGroup()
    {
        var doodad = CreateDoodad(
            clientDoodad: false,
            new DoodadFuncGroups
            {
                Id = 10,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                Model = "cgf://ordinary.cgf"
            },
            new DoodadFuncGroups
            {
                Id = 11,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                Model = "npctype://42"
            });

        await Assert.That(doodad.GetFuncGroupId()).IsEqualTo(10u);
    }

    [Test]
    public async Task GetFuncGroupId_ClientDoodadWithoutNpcModel_KeepsStartGroup()
    {
        var doodad = CreateDoodad(
            clientDoodad: true,
            new DoodadFuncGroups
            {
                Id = 20,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                Model = "cgf://ordinary.cgf"
            });

        await Assert.That(doodad.GetFuncGroupId()).IsEqualTo(20u);
    }

    [Test]
    public async Task ResolveInitialFuncGroupId_HonorsValidatedRetailPlacementPhase()
    {
        var doodad = CreateDoodad(
            clientDoodad: true,
            new DoodadFuncGroups
            {
                Id = 41492,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Start,
                Model = "npctype://10646"
            },
            new DoodadFuncGroups
            {
                Id = 41493,
                GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                Model = "npctype://10646"
            });
        doodad.TemplateId = 14073;

        await Assert.That(DoodadSpawner.ResolveInitialFuncGroupId(doodad, 41492)).IsEqualTo(41492u);
        await Assert.That(DoodadSpawner.ResolveInitialFuncGroupId(doodad, 99999)).IsEqualTo(41493u);
    }

    private static Doodad CreateDoodad(bool clientDoodad, params DoodadFuncGroups[] groups)
    {
        var template = new DoodadTemplate { ClientDoodad = clientDoodad };
        template.FuncGroups.AddRange(groups);
        return new Doodad { Template = template };
    }
}
