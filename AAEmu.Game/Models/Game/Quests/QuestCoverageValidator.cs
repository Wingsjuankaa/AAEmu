using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests;

public sealed record QuestCoverageFinding(
    string Code,
    uint ActId,
    string DetailType,
    uint DetailId,
    string Message);

/// <summary>
/// Runtime half of the Stage 40 quest coverage gate. It validates the exact enabled
/// base rows that survived context/component loading against the concrete detail
/// templates produced by every quest loader.
/// </summary>
public static class QuestCoverageValidator
{
    public static IReadOnlyList<QuestCoverageFinding> Validate(
        IEnumerable<QuestActTemplate> baseActs,
        IReadOnlyDictionary<string, Dictionary<uint, QuestActTemplate>> loadedByDetailType)
    {
        var findings = new List<QuestCoverageFinding>();
        var enabledActs = baseActs.Where(x => x.Enabled)
            .OrderBy(x => x.ActId)
            .ToArray();

        foreach (var baseAct in enabledActs)
        {
            if (string.IsNullOrWhiteSpace(baseAct.DetailType) ||
                !loadedByDetailType.TryGetValue(baseAct.DetailType, out var loadedType))
            {
                findings.Add(new QuestCoverageFinding(
                    "missing_server_class",
                    baseAct.ActId,
                    baseAct.DetailType ?? string.Empty,
                    baseAct.DetailId,
                    "Enabled quest act has no registered concrete QuestAct class."));
                continue;
            }

            if (!loadedType.TryGetValue(baseAct.DetailId, out var detail))
            {
                findings.Add(new QuestCoverageFinding(
                    "missing_detail_or_loader",
                    baseAct.ActId,
                    baseAct.DetailType,
                    baseAct.DetailId,
                    "Enabled quest act was not materialized by its detail-table loader."));
                continue;
            }

            if (detail.ActId != baseAct.ActId || detail.DetailId != baseAct.DetailId ||
                detail.GetType().Name != baseAct.DetailType ||
                detail.ParentComponent?.Id != baseAct.ParentComponent?.Id)
            {
                findings.Add(new QuestCoverageFinding(
                    "detail_attachment_mismatch",
                    baseAct.ActId,
                    baseAct.DetailType,
                    baseAct.DetailId,
                    "Loaded detail does not match the authored act id, type, detail id, or component."));
            }
        }

        var enabledKeys = enabledActs
            .Select(x => (x.ActId, x.DetailType, x.DetailId))
            .ToHashSet();
        foreach (var (detailType, details) in loadedByDetailType.OrderBy(x => x.Key))
        {
            foreach (var detail in details.Values.OrderBy(x => x.ActId))
            {
                if (!enabledKeys.Contains((detail.ActId, detailType, detail.DetailId)))
                {
                    findings.Add(new QuestCoverageFinding(
                        "orphan_detail_attachment",
                        detail.ActId,
                        detailType,
                        detail.DetailId,
                        "Concrete detail was attached without one exact enabled base act."));
                }
            }
        }

        return findings;
    }

    public static void Enforce(IReadOnlyList<QuestCoverageFinding> findings, QuestCoverageValidationMode mode)
    {
        if (mode != QuestCoverageValidationMode.Strict || findings.Count == 0)
            return;

        var first = findings[0];
        throw new InvalidDataException(
            $"Quest coverage strict gate failed with {findings.Count} finding(s). " +
            $"First: {first.Code} act={first.ActId} {first.DetailType}:{first.DetailId} - {first.Message}");
    }
}
