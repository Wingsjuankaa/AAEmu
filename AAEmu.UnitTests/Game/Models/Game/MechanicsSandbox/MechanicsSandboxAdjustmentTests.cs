using System.Text.Json;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxAdjustmentTests
{
    private static MechanicsSandboxConfig Configuration() => new()
    {
        Enabled = true, CharacterId = 1001, AccountId = 1, CharacterName = "Sandbox", ZoneKey = 379,
        Origin = new() { X = 500.295f, Y = 38373.5f, Z = 129.948f },
        Dummies = [new() { Forward = 5 }]
    };
    private static MechanicsSandboxConfig Copy(MechanicsSandboxConfig config) =>
        JsonSerializer.Deserialize<MechanicsSandboxConfig>(JsonSerializer.Serialize(config));

    [Test]
    public async Task AcceptedLayout_IsDetachedFromBothCallerAndActiveProfile()
    {
        var active = Configuration();
        var proposed = Copy(active);
        proposed.Origin.X = 502;
        proposed.Dummies = [new() { Forward = 7, Right = -1 }, new() { Forward = 12, Right = 1 }];
        var accepted = MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out var error);
        await Assert.That(accepted).IsTrue();
        await Assert.That(error).IsNull();
        await Assert.That(active.Origin.X).IsEqualTo(500.295f);
        await Assert.That(active.Dummies.Count).IsEqualTo(1);
        proposed.Origin.X = 600;
        proposed.Dummies[0].Forward = 55;
        await Assert.That(plan.Origin.X).IsEqualTo(502f);
        await Assert.That(plan.Dummies[0].Forward).IsEqualTo(7f);
        await Assert.That(plan.Dummies.Count).IsEqualTo(2);
    }

    [Test]
    public async Task FixedIdentityWorldZoneAndTemplateCannotBeChangedInALiveAdjustment()
    {
        Action<MechanicsSandboxConfig>[] edits =
        [
            c => c.Enabled = false, c => c.CharacterId = 2, c => c.AccountId = 2,
            c => c.CharacterName = "Dannia", c => c.WorldId = 1, c => c.InstanceId = 7,
            c => c.ZoneKey = 142, c => c.DummyTemplateId = 2308
        ];
        foreach (var edit in edits)
        {
            var active = Configuration();
            var before = JsonSerializer.Serialize(active);
            var proposed = Copy(active);
            edit(proposed);
            await Assert.That(MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out var error)).IsFalse();
            await Assert.That(plan).IsNull();
            await Assert.That(error).IsNotNull();
            await Assert.That(JsonSerializer.Serialize(active)).IsEqualTo(before);
        }
    }

    [Test]
    public async Task NonFiniteOutOfBoundsAndMoreThanSixteenDummies_AreRejectedWithoutChangingTheProfile()
    {
        Action<MechanicsSandboxConfig>[] edits =
        [
            c => c.Origin.Z = float.NaN,
            c => c.Dummies = Enumerable.Range(0, 17).Select(_ => new MechanicsSandboxDummy { Forward = 5 }).ToList(),
            c => c.Dummies[0].Forward = 61,
            c => c.Dummies[0].Right = float.PositiveInfinity,
            c => c.Dummies[0].Up = 11,
            c => c.Dummies.Clear()
        ];
        foreach (var edit in edits)
        {
            var active = Configuration();
            var before = JsonSerializer.Serialize(active);
            var proposed = Copy(active);
            edit(proposed);
            await Assert.That(MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out _)).IsFalse();
            await Assert.That(plan).IsNull();
            await Assert.That(JsonSerializer.Serialize(active)).IsEqualTo(before);
        }
    }

    [Test]
    public async Task LiveLayout_PreservesSceneAndDeepCopiesEveryServiceField()
    {
        var active = Configuration();
        active.SceneName = "Laboratorio de combate";
        active.Services = [new()
        {
            TemplateId = 42, Role = "specializations", Forward = -3, Right = -8, Up = 0.5f, Rotation = 1.25f
        }];
        var proposed = Copy(active);
        proposed.Dummies[0].Forward = 7;
        await Assert.That(MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out var error)).IsTrue();
        await Assert.That(error).IsNull();
        await Assert.That(plan.SceneName).IsEqualTo("Laboratorio de combate");
        await Assert.That(JsonSerializer.Serialize(plan.Services)).IsEqualTo(JsonSerializer.Serialize(active.Services));
        proposed.Services[0].TemplateId = 99;
        proposed.Services[0].Forward = 55;
        active.Services[0].Role = "warehouse";
        active.Services[0].Right = 55;
        await Assert.That(plan.Services[0].TemplateId).IsEqualTo(42u);
        await Assert.That(plan.Services[0].Role).IsEqualTo("specializations");
        await Assert.That(plan.Services[0].Forward).IsEqualTo(-3f);
        await Assert.That(plan.Services[0].Right).IsEqualTo(-8f);
        await Assert.That(plan.Services[0].Up).IsEqualTo(0.5f);
        await Assert.That(plan.Services[0].Rotation).IsEqualTo(1.25f);
        plan.Services.Clear();
        await Assert.That(active.Services.Count).IsEqualTo(1);
        await Assert.That(proposed.Services.Count).IsEqualTo(1);
    }

    [Test]
    public async Task LiveAdjustment_CannotRenameTheSceneOrAlterServicesEvenWithValidValues()
    {
        Action<MechanicsSandboxConfig>[] edits =
        [
            c => c.SceneName = "Otro escenario",
            c => c.Services[0].TemplateId = 2,
            c => c.Services[0].Role = "warehouse",
            c => c.Services[0].Forward = 4,
            c => c.Services[0].Right = 4,
            c => c.Services[0].Up = 1,
            c => c.Services[0].Rotation = 1,
            c => c.Services.Clear(),
            c => c.Services.Add(new() { TemplateId = 2, Role = "armor" })
        ];
        foreach (var edit in edits)
        {
            var active = Configuration();
            active.Services = [new() { TemplateId = 1, Role = "specializations" }];
            var before = JsonSerializer.Serialize(active);
            var proposed = Copy(active);
            edit(proposed);
            await Assert.That(MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out var error)).IsFalse();
            await Assert.That(plan).IsNull();
            await Assert.That(error).IsNotNull();
            await Assert.That(JsonSerializer.Serialize(active)).IsEqualTo(before);
        }
    }

    [Test]
    public async Task LegacyProfileWithNoServices_CanStillAdjustDummies()
    {
        var active = Configuration();
        active.Services = null;
        active.SceneName = null;
        var proposed = Copy(active);
        proposed.Dummies[0].Forward = 7;
        await Assert.That(MechanicsSandboxPolicy.TryPlanAdjustment(active, proposed, out var plan, out _)).IsTrue();
        await Assert.That(plan.Services.Count).IsEqualTo(0);
        await Assert.That(plan.SceneName).IsEqualTo("Laboratorio AA10");
    }
}
