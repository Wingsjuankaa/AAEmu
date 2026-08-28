namespace AAEmu.Game.Models.Game.Housing;

public enum HousingTerrainEnvelopeResult
{
    Accepted,
    TooHigh,
    TooLow,
    Invalid
}

/// <summary>Pure server-owned validation primitives for AA10 housing placement.</summary>
public static class HousingPlacementPolicy
{
    public static HousingItemHousings FindAuthorizedDesignItem(
        uint designId,
        uint itemTemplateId,
        ulong itemOwnerId,
        uint characterId,
        IReadOnlyCollection<HousingItemHousings> mappings)
    {
        if (designId == 0 || itemTemplateId == 0 || characterId == 0 ||
            itemOwnerId != characterId || mappings is null || mappings.Count == 0)
            return null;

        return mappings.FirstOrDefault(mapping => mapping is not null &&
            mapping.Design_Id == designId && mapping.Item_Id == itemTemplateId);
    }

    public static bool IsCategoryAllowedForFootprint(
        string world,
        double x,
        double y,
        double radius,
        uint categoryId,
        HousingAreaShapeCatalog areaShapes,
        IReadOnlyDictionary<uint, uint> areaGroups,
        IReadOnlyDictionary<uint, HashSet<uint>> groupCategories)
    {
        if (categoryId == 0 || radius <= 0d || double.IsNaN(radius) || double.IsInfinity(radius) ||
            areaShapes is null || areaGroups is null || areaGroups.Count == 0 ||
            groupCategories is null || groupCategories.Count == 0)
            return false;

        foreach (var areaId in areaShapes.FindContainingAreaIds(world, x, y, radius))
            if (areaGroups.TryGetValue(areaId, out var groupId) && groupId != 0 &&
                groupCategories.TryGetValue(groupId, out var categories) &&
                categories is not null && categories.Contains(categoryId))
                return true;
        return false;
    }

    public static bool HasFiniteTransform(float x, float y, float z, float rotation) =>
        IsFinite(x) && IsFinite(y) && IsFinite(z) && IsFinite(rotation);

    public static bool HasFiniteTransform(
        float x,
        float y,
        float z,
        float quaternionX,
        float quaternionY,
        float quaternionZ,
        float quaternionW) =>
        IsFinite(x) && IsFinite(y) && IsFinite(z) && IsFinite(quaternionX) &&
        IsFinite(quaternionY) && IsFinite(quaternionZ) && IsFinite(quaternionW);

    public static HousingTerrainEnvelopeResult EvaluateFootprintHeightEnvelope(
        float requestedHeight,
        float centerX,
        float centerY,
        float radius,
        float extraHeightAbove,
        float extraHeightBelow,
        Func<float, float, float> getTerrainHeight)
    {
        const float heightMapSpacing = 2f;
        if (!IsFinite(requestedHeight) || !IsFinite(centerX) || !IsFinite(centerY) ||
            !IsFinite(radius) || radius <= 0f || !IsFinite(extraHeightAbove) ||
            !IsFinite(extraHeightBelow) || extraHeightAbove < 0f || extraHeightBelow < 0f ||
            getTerrainHeight is null)
            return HousingTerrainEnvelopeResult.Invalid;

        var minimumTerrainHeight = float.PositiveInfinity;
        var maximumTerrainHeight = float.NegativeInfinity;
        if (!TryIncludeTerrainHeight(getTerrainHeight, centerX, centerY,
                ref minimumTerrainHeight, ref maximumTerrainHeight))
            return HousingTerrainEnvelopeResult.Invalid;

        var ringCount = Math.Max(1, (int)Math.Ceiling(radius / heightMapSpacing));
        for (var ringIndex = 1; ringIndex <= ringCount; ringIndex++)
        {
            var ringRadius = radius * ringIndex / ringCount;
            var sampleCount = Math.Max(8, (int)Math.Ceiling(2d * Math.PI * ringRadius / heightMapSpacing));
            for (var sampleIndex = 0; sampleIndex < sampleCount; sampleIndex++)
            {
                var angle = 2d * Math.PI * sampleIndex / sampleCount;
                if (!TryIncludeTerrainHeight(
                        getTerrainHeight,
                        centerX + ringRadius * (float)Math.Cos(angle),
                        centerY + ringRadius * (float)Math.Sin(angle),
                        ref minimumTerrainHeight,
                        ref maximumTerrainHeight))
                    return HousingTerrainEnvelopeResult.Invalid;
            }
        }

        if (requestedHeight - minimumTerrainHeight > extraHeightAbove)
            return HousingTerrainEnvelopeResult.TooHigh;
        if (maximumTerrainHeight - requestedHeight > extraHeightBelow)
            return HousingTerrainEnvelopeResult.TooLow;
        return HousingTerrainEnvelopeResult.Accepted;
    }

    public static bool CircularFootprintsOverlap(
        float x, float y, float radius, float otherX, float otherY, float otherRadius)
    {
        if (!IsFinite(x) || !IsFinite(y) || !IsFinite(radius) ||
            !IsFinite(otherX) || !IsFinite(otherY) || !IsFinite(otherRadius) ||
            radius < 0f || otherRadius < 0f)
            return true;

        // AA10 housing_size 1 intentionally has no placement footprint. It is
        // used by persisted system structures such as Archeum Lodestones; a
        // zero radius therefore cannot be promoted to an infinite blocker.
        // Requested player housing is still required to have radius > 0 by
        // IsCategoryAllowedForFootprint before this geometry primitive runs.
        if (radius == 0f || otherRadius == 0f)
            return false;

        var deltaX = (double)x - otherX;
        var deltaY = (double)y - otherY;
        var minimumDistance = (double)radius + otherRadius;
        return deltaX * deltaX + deltaY * deltaY < minimumDistance * minimumDistance;
    }

    private static bool TryIncludeTerrainHeight(
        Func<float, float, float> getTerrainHeight,
        float x,
        float y,
        ref float minimumTerrainHeight,
        ref float maximumTerrainHeight)
    {
        try
        {
            var height = getTerrainHeight(x, y);
            if (!IsFinite(height))
                return false;
            minimumTerrainHeight = Math.Min(minimumTerrainHeight, height);
            maximumTerrainHeight = Math.Max(maximumTerrainHeight, height);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static bool IsFinite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
}
