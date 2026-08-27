using System.Text.Json;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Items.Services;

public enum SummonMateBlockReason
{
    None,
    MissingSourceItem,
    SourceNotOwned,
    SourceNotInInventory,
    WrongItemType,
    BlockedContract,
    SkillMismatch,
    RuntimeDataMismatch
}

public sealed record SummonMateContract(uint ItemId, uint SkillId, uint NpcId);

/// <summary>
/// Closed AA10 retail catalogue for item-backed mate summons.  The service is
/// populated once from a generated manifest policy; unknown relationships are
/// never delegated to the legacy item_summon_mates path.
/// </summary>
public sealed class SummonMateContractService : Singleton<SummonMateContractService>
{
    internal const string RuntimePolicyPath = "Data/aa10-summon-mate-policy-v1.json";
    internal const string PolicyFormat = "aa10-summon-mate-runtime-policy-v1";

    private Dictionary<uint, SummonMateContract> _contracts = [];

    public int Count => _contracts.Count;

    public void Load(IReadOnlyDictionary<uint, ItemTemplate> templates, string path = RuntimePolicyPath)
    {
        ArgumentNullException.ThrowIfNull(templates);
        var policy = LoadRuntimePolicy(path);
        var contracts = new Dictionary<uint, SummonMateContract>();

        foreach (var entry in policy.Contracts)
        {
            if (!templates.TryGetValue(entry.ItemId, out var template) ||
                template is not SummonMateTemplate mateTemplate ||
                template.ImplId != ItemImplEnum.SummonMate ||
                template.UseSkillAsReagent ||
                template.UseSkillId != entry.SkillId ||
                mateTemplate.NpcId != entry.NpcId)
            {
                throw new InvalidDataException(
                    $"AA10 summon-mate policy/runtime mismatch for item {entry.ItemId}.");
            }

            contracts.Add(entry.ItemId, new SummonMateContract(entry.ItemId, entry.SkillId, entry.NpcId));
        }

        _contracts = contracts;
    }

    public bool TryGetContract(uint itemTemplateId, out SummonMateContract contract) =>
        _contracts.TryGetValue(itemTemplateId, out contract);

    public bool TryResolve(
        Item sourceItem,
        uint castSkillId,
        uint ownerId,
        out SummonMateContract contract,
        out SummonMateBlockReason failure)
    {
        contract = null;
        if (sourceItem is null)
        {
            failure = SummonMateBlockReason.MissingSourceItem;
            return false;
        }
        if (sourceItem.OwnerId != ownerId)
        {
            failure = SummonMateBlockReason.SourceNotOwned;
            return false;
        }
        if (sourceItem.Id == 0 || sourceItem.Count <= 0 ||
            sourceItem.SlotType != SlotType.Inventory ||
            sourceItem._holdingContainer is not { ContainerType: SlotType.Inventory } container ||
            container.OwnerId != ownerId || !container.Items.Contains(sourceItem))
        {
            failure = SummonMateBlockReason.SourceNotInInventory;
            return false;
        }
        if (sourceItem is not SummonMate || sourceItem.Template is not SummonMateTemplate runtimeTemplate)
        {
            failure = SummonMateBlockReason.WrongItemType;
            return false;
        }
        if (!_contracts.TryGetValue(sourceItem.TemplateId, out contract))
        {
            failure = SummonMateBlockReason.BlockedContract;
            return false;
        }
        if (castSkillId != contract.SkillId)
        {
            failure = SummonMateBlockReason.SkillMismatch;
            contract = null;
            return false;
        }
        if (runtimeTemplate.Id != contract.ItemId || runtimeTemplate.UseSkillId != contract.SkillId ||
            runtimeTemplate.NpcId != contract.NpcId || runtimeTemplate.UseSkillAsReagent ||
            runtimeTemplate.ImplId != ItemImplEnum.SummonMate)
        {
            failure = SummonMateBlockReason.RuntimeDataMismatch;
            contract = null;
            return false;
        }

        failure = SummonMateBlockReason.None;
        return true;
    }

    internal static SummonMateRuntimePolicy LoadRuntimePolicy(string path)
    {
        if (!File.Exists(path))
            throw new FileNotFoundException(
                "AA10 summon-mate runtime policy is required; mate items cannot fall back to legacy.", path);

        var policy = JsonSerializer.Deserialize<SummonMateRuntimePolicy>(
            File.ReadAllText(path),
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
        if (policy is null || policy.Format != PolicyFormat ||
            string.IsNullOrWhiteSpace(policy.SourceManifestSha256) ||
            policy.Contracts is null || policy.Contracts.Count == 0)
            throw new InvalidDataException("AA10 summon-mate runtime policy is invalid or empty.");

        if (policy.SourceManifestSha256.Length != 64 ||
            policy.SourceManifestSha256.Any(value => !Uri.IsHexDigit(value)))
            throw new InvalidDataException("AA10 summon-mate runtime policy has an invalid manifest hash.");

        var itemIds = new HashSet<uint>();
        foreach (var contract in policy.Contracts)
        {
            if (contract.ItemId == 0 || contract.SkillId == 0 || contract.NpcId == 0 ||
                !itemIds.Add(contract.ItemId))
                throw new InvalidDataException(
                    "AA10 summon-mate runtime policy contains zero or duplicate contract IDs.");
        }

        return policy;
    }

    internal sealed class SummonMateRuntimePolicy
    {
        public string Format { get; init; }
        public string SourceManifestSha256 { get; init; }
        public List<SummonMateRuntimeContract> Contracts { get; init; }
    }

    internal sealed class SummonMateRuntimeContract
    {
        public uint ItemId { get; init; }
        public uint SkillId { get; init; }
        public uint NpcId { get; init; }
    }
}
