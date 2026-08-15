namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>
/// Resolves the synthesis-effect groups an item keeps and gains while it is synthesized or awakened.
/// Group ids are category-local, so awakening inherits the attribute/type pair rather than copying an
/// id that belongs to the category the item just left.
/// </summary>
internal static class ItemRandomAttributeResolver
{
    internal sealed record Resolution(
        bool IsValid,
        IReadOnlyList<uint> GroupIds,
        IReadOnlyList<uint> AddedGroupIds,
        string FailureReason)
    {
        internal static Resolution Fail(string reason) => new(false, [], [], reason);
    }

    internal static Resolution ResolveForSynthesis(
        ItemRndAttrCategory category,
        byte grade,
        IEnumerable<uint> existingGroupIds,
        Func<int, int> nextRandom)
    {
        if (category is null)
            return Resolution.Fail("The target synthesis category is missing.");
        if (nextRandom is null)
            throw new ArgumentNullException(nameof(nextRandom));

        var maximum = Math.Clamp(
            category.GetProperty(grade)?.MaxUnitModifierNum ?? 0,
            0,
            EquipItem.RndAttrSlots);
        var sets = category.GroupSets.OrderBy(set => set.Id).ToArray();
        var groupsById = sets
            .SelectMany(set => set.Groups)
            .ToDictionary(group => group.Id);
        var selected = new List<ItemRndAttrUnitModifierGroup>();
        var selectedIds = new HashSet<uint>();
        var usedAttributes = new HashSet<uint>();

        foreach (var id in existingGroupIds ?? [])
        {
            if (!groupsById.TryGetValue(id, out var group) || !group.ValueByGrade.ContainsKey(grade))
                return Resolution.Fail($"Existing synthesis-effect group {id} is not valid for category {category.Id}, grade {grade}.");
            if (!selectedIds.Add(id) || !usedAttributes.Add(group.UnitAttributeId))
                return Resolution.Fail($"Existing synthesis-effect group {id} duplicates a group or attribute.");
            selected.Add(group);
        }

        if (selected.Count > maximum)
            return Resolution.Fail($"The item carries {selected.Count} synthesis effects but grade {grade} permits {maximum}.");

        var added = new List<uint>();
        foreach (var set in sets)
        {
            if (selected.Count >= maximum)
                break;

            var selectedInSet = selected.Count(group => group.GroupSetId == set.Id);
            var quota = Math.Min(
                Math.Max(set.PickNum - selectedInSet, 0),
                maximum - selected.Count);

            for (var pick = 0; pick < quota; pick++)
            {
                var candidates = set.Groups
                    .Where(group =>
                        group.ValueByGrade.ContainsKey(grade) &&
                        !selectedIds.Contains(group.Id) &&
                        !usedAttributes.Contains(group.UnitAttributeId))
                    .ToList();
                if (candidates.Count == 0)
                    return Resolution.Fail($"Synthesis-effect set {set.Id} cannot satisfy its pick count at grade {grade}.");

                var fixedCandidates = candidates.Where(group => group.FixedAttr).ToList();
                var chosen = PickWeighted(fixedCandidates.Count > 0 ? fixedCandidates : candidates, nextRandom);
                selected.Add(chosen);
                selectedIds.Add(chosen.Id);
                usedAttributes.Add(chosen.UnitAttributeId);
                added.Add(chosen.Id);
            }
        }

        if (selected.Count != maximum)
            return Resolution.Fail($"Category {category.Id}, grade {grade} requires {maximum} synthesis effects but only {selected.Count} were resolved.");

        return new Resolution(true, selected.Select(group => group.Id).ToArray(), added, null);
    }

    internal static Resolution ResolveForAwakening(
        ItemRndAttrCategory sourceCategory,
        ItemRndAttrCategory targetCategory,
        byte targetGrade,
        IEnumerable<uint> sourceGroupIds,
        Func<int, int> nextRandom)
    {
        if (targetCategory is null)
            return Resolution.Fail("The awakening target category is missing.");

        var sourceIds = (sourceGroupIds ?? []).ToArray();
        var targetMaximum = Math.Clamp(
            targetCategory.GetProperty(targetGrade)?.MaxUnitModifierNum ?? 0,
            0,
            EquipItem.RndAttrSlots);

        // Some mappings only change the template while staying in one synthesis category. Its group
        // ids remain valid and must not follow inherit_priority_id, which points to a later category.
        if (sourceCategory?.Id == targetCategory.Id)
            return ResolveForSynthesis(targetCategory, targetGrade, sourceIds, nextRandom);

        // A target grade with no synthesis-effect slots deliberately sheds source lines. Trying to map
        // them into a category that cannot represent any would turn a valid non-effect awakening into
        // a hard failure.
        if (targetMaximum == 0)
            return ResolveForSynthesis(targetCategory, targetGrade, [], nextRandom);

        if (sourceIds.Length > 0 && sourceCategory is null)
            return Resolution.Fail("The awakening source category is missing for existing synthesis effects.");

        var mapped = new List<uint>();
        var sourceGroups = sourceCategory?.GroupSets
            .SelectMany(set => set.Groups)
            .ToDictionary(group => group.Id) ?? [];

        foreach (var sourceId in sourceIds)
        {
            if (!sourceGroups.TryGetValue(sourceId, out var sourceGroup))
                return Resolution.Fail($"Awakening source group {sourceId} does not belong to category {sourceCategory.Id}.");

            var sourceSet = sourceCategory.GroupSets.SingleOrDefault(set => set.Id == sourceGroup.GroupSetId);
            if (sourceSet is null)
                return Resolution.Fail($"Awakening source set {sourceGroup.GroupSetId} is missing.");

            ItemRndAttrUnitModifierGroupSet targetSet = null;
            if (sourceSet.InheritPriorityId != 0)
            {
                targetSet = targetCategory.GroupSets.SingleOrDefault(set => set.Id == sourceSet.InheritPriorityId);
            }
            else
            {
                var candidates = targetCategory.GroupSets
                    .Where(set => set.Groups.Any(group =>
                        group.UnitAttributeId == sourceGroup.UnitAttributeId &&
                        group.UnitModifierTypeId == sourceGroup.UnitModifierTypeId &&
                        group.ValueByGrade.ContainsKey(targetGrade)))
                    .ToArray();
                if (candidates.Length == 1)
                    targetSet = candidates[0];
            }

            var targetGroup = targetSet?.Groups.SingleOrDefault(group =>
                group.UnitAttributeId == sourceGroup.UnitAttributeId &&
                group.UnitModifierTypeId == sourceGroup.UnitModifierTypeId &&
                group.ValueByGrade.ContainsKey(targetGrade));
            if (targetGroup is null)
            {
                return Resolution.Fail(
                    $"No unambiguous target group inherits attribute {sourceGroup.UnitAttributeId}, " +
                    $"type {sourceGroup.UnitModifierTypeId} from source group {sourceId}.");
            }

            mapped.Add(targetGroup.Id);
        }

        // Awakening preserves every mapped line, then draws only the newly unlocked slots at the
        // resulting grade. Explorer rank 1 therefore gains its first line; rank 2 keeps that line and
        // gains the second; the Hiram conversion keeps both and gains the third.
        return ResolveForSynthesis(targetCategory, targetGrade, mapped, nextRandom);
    }

    private static ItemRndAttrUnitModifierGroup PickWeighted(
        IReadOnlyList<ItemRndAttrUnitModifierGroup> candidates,
        Func<int, int> nextRandom)
    {
        var total = candidates.Sum(group => Math.Max(1, group.Weight));
        var roll = nextRandom(total);
        if (roll is < 0 || roll >= total)
            throw new ArgumentOutOfRangeException(nameof(nextRandom), $"Random selector returned {roll} for bound {total}.");

        foreach (var group in candidates)
        {
            roll -= Math.Max(1, group.Weight);
            if (roll < 0)
                return group;
        }

        return candidates[^1];
    }
}
