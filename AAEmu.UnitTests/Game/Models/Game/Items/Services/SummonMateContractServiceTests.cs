using System.Security.Cryptography;
using System.Text.Json;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Services;

public class SummonMateContractServiceTests
{
    private static string PolicyPath =>
        Path.Combine(AppContext.BaseDirectory, "Data", "aa10-summon-mate-policy-v1.json");

    [Test]
    public async Task RuntimePolicyIsClosedAndMatchesCommittedManifest()
    {
        var policy = SummonMateContractService.LoadRuntimePolicy(PolicyPath);
        var repository = FindRepositoryRoot();
        var manifestPath = Path.Combine(
            repository,
            "reconstruccion_cliente_10",
            "evidence",
            "summon_mates",
            "aa10-summon-mate-manifest-v1.json");
        var manifestBytes = File.ReadAllBytes(manifestPath);
        using var manifest = JsonDocument.Parse(manifestBytes);

        await Assert.That(policy.Contracts).Count().IsEqualTo(478);
        await Assert.That(policy.Contracts.Select(contract => contract.ItemId).Distinct()).Count()
            .IsEqualTo(478);
        await Assert.That(Convert.ToHexString(SHA256.HashData(manifestBytes)))
            .IsEqualTo(policy.SourceManifestSha256);
        await Assert.That(manifest.RootElement.GetProperty("summary").GetProperty("relations").GetInt32())
            .IsEqualTo(552);
        await Assert.That(manifest.RootElement.GetProperty("summary").GetProperty("blocked").GetInt32())
            .IsEqualTo(74);
        var rows = manifest.RootElement.GetProperty("rows").EnumerateArray().ToArray();
        await Assert.That(rows.Count(row => row.GetProperty("state").GetString() == "executable"))
            .IsEqualTo(478);
        await Assert.That(rows.Count(row => HasBlocker(row, "compact:missing_item"))).IsEqualTo(71);
        await Assert.That(rows.Count(row => HasBlocker(row, "compact:missing_npc"))).IsEqualTo(1);
        await Assert.That(rows.Count(row => HasBlocker(row, "compact:missing_initial_buff"))).IsEqualTo(2);

        var executable = rows
            .Where(row => row.GetProperty("state").GetString() == "executable")
            .ToDictionary(
                row => row.GetProperty("itemId").GetUInt32(),
                row => (
                    SkillId: row.GetProperty("compact").GetProperty("skillId").GetUInt32(),
                    NpcId: row.GetProperty("npcId").GetUInt32()));
        var policyMismatches = policy.Contracts
            .Where(contract =>
                !executable.TryGetValue(contract.ItemId, out var expected) ||
                expected.SkillId != contract.SkillId ||
                expected.NpcId != contract.NpcId)
            .Select(contract => contract.ItemId)
            .ToArray();

        await Assert.That(policyMismatches).IsEmpty();
        await Assert.That(executable.Keys.Except(policy.Contracts.Select(contract => contract.ItemId)))
            .IsEmpty();
    }

    [Test]
    public async Task PolicyRuntimeMismatchStopsStartup()
    {
        var policy = SummonMateContractService.LoadRuntimePolicy(PolicyPath);
        var templates = Templates(policy);
        var first = policy.Contracts[0];
        ((SummonMateTemplate)templates[first.ItemId]).NpcId++;
        var service = new SummonMateContractService();

        await Assert.That(() => service.Load(templates, PolicyPath)).Throws<InvalidDataException>();
    }

    [Test]
    public async Task ExactPhysicalInventoryItemResolves()
    {
        var service = CreateLoadedService(out var contract);
        var template = Template(contract);
        var item = new SummonMate(9001, template, 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory,
            Slot = 3
        };
        PlaceInContainer(item, 42, SlotType.Inventory);

        var resolved = service.TryResolve(item, contract.SkillId, 42, out var actual, out var failure);

        await Assert.That(resolved).IsTrue();
        await Assert.That(actual).IsEqualTo(contract);
        await Assert.That(failure).IsEqualTo(SummonMateBlockReason.None);
    }

    [Test]
    [Arguments(41u, SlotType.Inventory, 100u, SummonMateBlockReason.SourceNotOwned)]
    [Arguments(42u, SlotType.Bank, 100u, SummonMateBlockReason.SourceNotInInventory)]
    [Arguments(42u, SlotType.Inventory, 101u, SummonMateBlockReason.SkillMismatch)]
    public async Task OwnerSlotAndSkillMismatchesFailClosed(
        uint ownerId,
        SlotType slotType,
        uint skillId,
        SummonMateBlockReason expected)
    {
        var service = CreateLoadedService(out var contract);
        var item = new SummonMate(9001, Template(contract), 1)
        {
            OwnerId = ownerId,
            SlotType = slotType
        };
        PlaceInContainer(item, ownerId, slotType);

        var resolved = service.TryResolve(item, skillId, 42, out _, out var failure);

        await Assert.That(resolved).IsFalse();
        await Assert.That(failure).IsEqualTo(expected);
    }

    [Test]
    public async Task UnknownItemNeverFallsBackToRuntimeRelation()
    {
        var service = CreateLoadedService(out _);
        var template = new SummonMateTemplate
        {
            Id = 999,
            NpcId = 300,
            UseSkillId = 100,
            ImplId = ItemImplEnum.SummonMate
        };
        var item = new SummonMate(9002, template, 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        PlaceInContainer(item, 42, SlotType.Inventory);

        var resolved = service.TryResolve(item, 100, 42, out _, out var failure);

        await Assert.That(resolved).IsFalse();
        await Assert.That(failure).IsEqualTo(SummonMateBlockReason.BlockedContract);
    }

    [Test]
    public async Task InvalidPhysicalItemIdentityFailsBeforeContractResolution()
    {
        var service = CreateLoadedService(out var contract);
        var zeroId = new SummonMate(0, Template(contract), 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        PlaceInContainer(zeroId, 42, SlotType.Inventory);
        var zeroCount = new SummonMate(9002, Template(contract), 0)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        PlaceInContainer(zeroCount, 42, SlotType.Inventory);
        var detached = new SummonMate(9003, Template(contract), 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        detached._holdingContainer = new ItemContainer(42, SlotType.Inventory, false, null);

        await Assert.That(service.TryResolve(zeroId, contract.SkillId, 42, out _, out var zeroIdFailure))
            .IsFalse();
        await Assert.That(zeroIdFailure).IsEqualTo(SummonMateBlockReason.SourceNotInInventory);
        await Assert.That(service.TryResolve(zeroCount, contract.SkillId, 42, out _, out var zeroCountFailure))
            .IsFalse();
        await Assert.That(zeroCountFailure).IsEqualTo(SummonMateBlockReason.SourceNotInInventory);
        await Assert.That(service.TryResolve(detached, contract.SkillId, 42, out _, out var detachedFailure))
            .IsFalse();
        await Assert.That(detachedFailure).IsEqualTo(SummonMateBlockReason.SourceNotInInventory);
    }

    [Test]
    public async Task WrongRuntimeTypeAndRelationDriftFailClosed()
    {
        var service = CreateLoadedService(out var contract);
        var plainItem = new Item(9004, new ItemTemplate
        {
            Id = contract.ItemId,
            UseSkillId = contract.SkillId,
            ImplId = ItemImplEnum.Misc
        }, 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        PlaceInContainer(plainItem, 42, SlotType.Inventory);
        var driftedTemplate = Template(contract);
        driftedTemplate.NpcId++;
        var driftedMate = new SummonMate(9005, driftedTemplate, 1)
        {
            OwnerId = 42,
            SlotType = SlotType.Inventory
        };
        PlaceInContainer(driftedMate, 42, SlotType.Inventory);

        await Assert.That(service.TryResolve(plainItem, contract.SkillId, 42, out _, out var typeFailure))
            .IsFalse();
        await Assert.That(typeFailure).IsEqualTo(SummonMateBlockReason.WrongItemType);
        await Assert.That(service.TryResolve(driftedMate, contract.SkillId, 42, out _, out var driftFailure))
            .IsFalse();
        await Assert.That(driftFailure).IsEqualTo(SummonMateBlockReason.RuntimeDataMismatch);
    }

    private static SummonMateContractService CreateLoadedService(out SummonMateContract contract)
    {
        var service = new SummonMateContractService();
        var policy = SummonMateContractService.LoadRuntimePolicy(PolicyPath);
        var templates = Templates(policy);
        service.Load(templates, PolicyPath);
        var first = policy.Contracts[0];
        contract = new SummonMateContract(first.ItemId, first.SkillId, first.NpcId);
        return service;
    }

    private static Dictionary<uint, ItemTemplate> Templates(
        SummonMateContractService.SummonMateRuntimePolicy policy) =>
        policy.Contracts.ToDictionary(
            entry => entry.ItemId,
            entry => (ItemTemplate)new SummonMateTemplate
            {
                Id = entry.ItemId,
                NpcId = entry.NpcId,
                UseSkillId = entry.SkillId,
                ImplId = ItemImplEnum.SummonMate,
                UseSkillAsReagent = false
            });

    private static bool HasBlocker(JsonElement row, string blocker) =>
        row.GetProperty("blockers").EnumerateArray().Any(value => value.GetString() == blocker);

    private static SummonMateTemplate Template(SummonMateContract contract) => new()
    {
        Id = contract.ItemId,
        NpcId = contract.NpcId,
        UseSkillId = contract.SkillId,
        ImplId = ItemImplEnum.SummonMate,
        UseSkillAsReagent = false
    };

    private static void PlaceInContainer(Item item, uint ownerId, SlotType slotType)
    {
        var container = new ItemContainer(ownerId, slotType, false, null);
        container.Items.Add(item);
        item._holdingContainer = container;
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "AAEmu.slnx")))
            directory = directory.Parent;
        return directory?.FullName ?? throw new DirectoryNotFoundException("AAEmu repository root not found.");
    }
}
