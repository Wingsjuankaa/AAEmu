using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using Microsoft.Extensions.Configuration;
using System.Text;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxPolicyTests
{
    private static MechanicsSandboxConfig Config() => new()
    {
        Enabled = true, CharacterId = 1001, AccountId = 1, CharacterName = "Sandbox", ZoneKey = 379,
        Origin = new() { X = 500.295f, Y = 38373.5f, Z = 129.948f },
        Dummies = [new() { Forward = 5 }]
    };
    private static MechanicsSandboxIdentity Identity() => new(1001, 1, "Sandbox", 0, 0, 379);

    [Test]
    public async Task DefaultConfiguration_IsDisabled()
    {
        await Assert.That(MechanicsSandboxPolicy.Validate(new(), Identity())).IsNotNull();
    }

    private static ConfigurationRoot JsonConfiguration()
    {
        const string json = """
        {"MechanicsSandbox":{"Enabled":true,"CharacterName":"Sandbox","CharacterId":1001,"AccountId":1,
        "ZoneKey":379,"Origin":{"X":500.295,"Y":38373.5,"Z":129.948,"Rotation":0},
        "Dummies":[{"Forward":5},{"Forward":10,"Right":-2},{"Forward":10},{"Forward":10,"Right":2}]}}
        """;
        return (ConfigurationRoot)new ConfigurationBuilder().AddJsonStream(new MemoryStream(Encoding.UTF8.GetBytes(json))).Build();
    }

    [Test]
    public async Task RealConfigurationBinder_DoesNotAppendDefaultDummiesToTheFourConfiguredSlots()
    {
        using var json = JsonConfiguration();
        var configuration = new AppConfiguration();
        json.Bind(configuration);
        await Assert.That(configuration.MechanicsSandbox.Dummies.Count).IsEqualTo(4);
        await Assert.That(configuration.MechanicsSandbox.Services.Count).IsEqualTo(0);
        await Assert.That(configuration.MechanicsSandbox.SceneName).IsEqualTo("Laboratorio AA10");
        await Assert.That(MechanicsSandboxPolicy.Validate(configuration.MechanicsSandbox, Identity())).IsNull();
    }

    [Test]
    public async Task RealConfigurationReload_ReplacesSandboxSlotsRatherThanAppendingDuplicates()
    {
        using var json = JsonConfiguration();
        var configuration = new AppConfiguration();
        json.Bind(configuration);
        for (var reload = 0; reload < 3; reload++)
        {
            global::AAEmu.Game.Program.BindReloadedConfiguration(json, configuration);
            await Assert.That(configuration.MechanicsSandbox.Dummies.Count).IsEqualTo(4);
            await Assert.That(configuration.MechanicsSandbox.Dummies[1].Right).IsEqualTo(-2f);
        }
    }

    [Test]
    public async Task RealConfigurationReload_PreservesConfiguredServicesWithoutAppendingDuplicates()
    {
        const string jsonText = """
        {"MechanicsSandbox":{"Enabled":true,"CharacterName":"Sandbox","CharacterId":1001,"AccountId":1,
        "ZoneKey":379,"SceneName":"Laboratorio de combate","Origin":{"X":500.295,"Y":38373.5,"Z":129.948},
        "Dummies":[{"Forward":5}],"Services":[
        {"TemplateId":1,"Role":"specializations","Forward":-3,"Right":-8,"Up":0.5,"Rotation":1.25},
        {"TemplateId":2,"Role":"warehouse","Forward":-6,"Right":-8}]}}
        """;
        using var json = (ConfigurationRoot)new ConfigurationBuilder()
            .AddJsonStream(new MemoryStream(Encoding.UTF8.GetBytes(jsonText))).Build();
        var configuration = new AppConfiguration();
        json.Bind(configuration);
        for (var reload = 0; reload < 3; reload++)
        {
            global::AAEmu.Game.Program.BindReloadedConfiguration(json, configuration);
            await Assert.That(configuration.MechanicsSandbox.Services.Count).IsEqualTo(2);
            await Assert.That(configuration.MechanicsSandbox.SceneName).IsEqualTo("Laboratorio de combate");
            await Assert.That(configuration.MechanicsSandbox.Services[0].Up).IsEqualTo(0.5f);
            await Assert.That(configuration.MechanicsSandbox.Services[0].Rotation).IsEqualTo(1.25f);
            await Assert.That(MechanicsSandboxPolicy.Validate(configuration.MechanicsSandbox, Identity())).IsNull();
        }
    }

    [Test]
    public async Task OnlyTheExplicitCharacterAccountAndZoneBindingIsAccepted()
    {
        var config = Config();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNull();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity() with { CharacterId = 1002 })).IsNotNull();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity() with { AccountId = 2 })).IsNotNull();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity() with { Name = "Dannia" })).IsNotNull();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity() with { ZoneKey = 142 })).IsNotNull();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity() with { InstanceId = 7 })).IsNotNull();
    }

    [Test]
    public async Task NonFinitePositionsOrMissingActors_AreRejectedBeforeMutation()
    {
        var config = Config();
        config.Origin.X = float.NaN;
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNotNull();
        config = Config();
        config.Dummies[0].Forward = float.PositiveInfinity;
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNotNull();
        config = Config();
        config.Dummies.Clear();
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNotNull();
        config = Config();
        config.CharacterId = 0;
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNotNull();
    }

    [Test]
    public async Task MissingNewFieldsOnAnExistingInstance_ReceiveLazyCompatibleDefaults()
    {
        var config = Config();
        config.SceneName = null;
        config.Services = null;
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNull();
        await Assert.That(config.SceneName).IsEqualTo("Laboratorio AA10");
        await Assert.That(config.Services.Count).IsEqualTo(0);
        await Assert.That(new MechanicsSandboxConfig().Dummies.Count).IsEqualTo(0);
    }

    [Test]
    public async Task ServiceRolesAndFiniteBoundaryPositions_AreAcceptedWithoutInferringTemplateCapabilities()
    {
        var config = Config();
        config.Services = [
            new() { TemplateId = 1, Role = "specializations", Forward = -60, Right = 60, Up = -10, Rotation = MathF.PI },
            new() { TemplateId = 2, Role = "warehouse", Forward = 60, Right = -60, Up = 10 },
            new() { TemplateId = 3, Role = "weapons" },
            new() { TemplateId = 3, Role = "armor" }
        ];
        // Pure policy checks shape; the manager must check each native template's actual role.
        await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNull();
    }

    [Test]
    public async Task InvalidServiceDefinitions_AreRejected()
    {
        Action<MechanicsSandboxConfig>[] edits =
        [
            c => c.SceneName = " ",
            c => c.Services[0].TemplateId = 0,
            c => c.Services[0].Role = "merchant",
            c => c.Services[0].Role = "Specializations",
            c => c.Services[0].Role = null,
            c => c.Services[0].Forward = 60.01f,
            c => c.Services[0].Right = -60.01f,
            c => c.Services[0].Up = 10.01f,
            c => c.Services[0].Forward = float.NaN,
            c => c.Services[0].Rotation = float.PositiveInfinity,
            c => c.Services[0] = null,
            c => c.Services.Add(new() { TemplateId = 2, Role = "specializations" }),
            c => c.Services = Enumerable.Range(1, 9).Select(i =>
                new MechanicsSandboxServiceNpc { TemplateId = (uint)i, Role = "specializations" }).ToList()
        ];
        foreach (var edit in edits)
        {
            var config = Config();
            config.Services = [new() { TemplateId = 1, Role = "specializations" }];
            edit(config);
            await Assert.That(MechanicsSandboxPolicy.Validate(config, Identity())).IsNotNull();
        }
    }
}
