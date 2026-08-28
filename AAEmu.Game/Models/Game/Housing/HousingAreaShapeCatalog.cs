namespace AAEmu.Game.Models.Game.Housing;

public sealed class HousingAreaShapePoint
{
    public double X { get; set; }
    public double Y { get; set; }
}

public sealed class HousingAreaShapeTemplate
{
    public uint AreaId { get; set; }
    public uint ZoneId { get; set; }
    public string World { get; set; }
    public string EntityGuid { get; set; }
    public double MinX { get; set; }
    public double MinY { get; set; }
    public double MaxX { get; set; }
    public double MaxY { get; set; }
    public List<HousingAreaShapePoint> Points { get; set; }
}

public sealed class HousingAreaShapeFile
{
    public int SchemaVersion { get; set; }
    public string Source { get; set; }
    public List<HousingAreaShapeTemplate> Shapes { get; set; }
}

/// <summary>
/// Immutable point-in-polygon catalogue reconstructed from the AA10 r575
/// main_world LevelDesignShape housing_area.xml files.
/// </summary>
public sealed class HousingAreaShapeCatalog
{
    private const double BoundaryEpsilon = 0.00001d;
    private readonly Dictionary<string, List<HousingAreaShapeTemplate>> _shapesByWorld;

    private HousingAreaShapeCatalog(Dictionary<string, List<HousingAreaShapeTemplate>> shapesByWorld)
    {
        _shapesByWorld = shapesByWorld;
        ShapeCount = shapesByWorld.Values.Sum(shapes => shapes.Count);
        AreaCount = shapesByWorld.Values
            .SelectMany(shapes => shapes)
            .Select(shape => shape.AreaId)
            .Distinct()
            .Count();
    }

    public int ShapeCount { get; }
    public int AreaCount { get; }
    public int WorldCount => _shapesByWorld.Count;

    public static HousingAreaShapeCatalog Empty { get; } = Create([]);

    public static HousingAreaShapeCatalog Create(IEnumerable<HousingAreaShapeTemplate> candidates)
    {
        var byWorld = new Dictionary<string, List<HousingAreaShapeTemplate>>(StringComparer.Ordinal);
        if (candidates is null)
            return new HousingAreaShapeCatalog(byWorld);

        foreach (var shape in candidates)
        {
            if (shape is null || shape.AreaId == 0 || string.IsNullOrEmpty(shape.World) ||
                shape.Points is null || shape.Points.Count < 3 || !HasFiniteBounds(shape) ||
                shape.MinX > shape.MaxX || shape.MinY > shape.MaxY ||
                shape.Points.Any(point => point is null || !IsFinite(point.X) || !IsFinite(point.Y)))
                continue;

            if (!byWorld.TryGetValue(shape.World, out var shapes))
                byWorld.Add(shape.World, shapes = []);
            shapes.Add(shape);
        }

        foreach (var shapes in byWorld.Values)
            shapes.Sort((left, right) =>
            {
                var areaOrder = left.AreaId.CompareTo(right.AreaId);
                return areaOrder != 0
                    ? areaOrder
                    : string.Compare(left.EntityGuid, right.EntityGuid, StringComparison.Ordinal);
            });

        return new HousingAreaShapeCatalog(byWorld);
    }

    public IReadOnlyCollection<uint> FindContainingAreaIds(string world, double x, double y, double radius)
    {
        if (string.IsNullOrEmpty(world) || !IsFinite(x) || !IsFinite(y) ||
            !IsFinite(radius) || radius <= 0d || !_shapesByWorld.TryGetValue(world, out var shapes))
            return [];

        var result = new HashSet<uint>();
        foreach (var shape in shapes)
            if (ContainsCircle(shape, x, y, radius))
                result.Add(shape.AreaId);
        return result.ToArray();
    }

    public static bool ContainsPoint(HousingAreaShapeTemplate shape, double x, double y)
    {
        if (shape?.Points is null || shape.Points.Count < 3 || !IsFinite(x) || !IsFinite(y) ||
            x < shape.MinX - BoundaryEpsilon || x > shape.MaxX + BoundaryEpsilon ||
            y < shape.MinY - BoundaryEpsilon || y > shape.MaxY + BoundaryEpsilon)
            return false;

        var inside = false;
        for (int current = 0, previous = shape.Points.Count - 1;
             current < shape.Points.Count;
             previous = current++)
        {
            var a = shape.Points[previous];
            var b = shape.Points[current];
            if (IsOnSegment(a, b, x, y))
                return true;
            if ((a.Y > y) == (b.Y > y))
                continue;
            var intersectionX = (b.X - a.X) * (y - a.Y) / (b.Y - a.Y) + a.X;
            if (x < intersectionX)
                inside = !inside;
        }
        return inside;
    }

    /// <summary>True only when the complete circular AA10 housing footprint fits one polygon.</summary>
    public static bool ContainsCircle(HousingAreaShapeTemplate shape, double x, double y, double radius)
    {
        if (shape?.Points is null || shape.Points.Count < 3 || !IsFinite(x) || !IsFinite(y) ||
            !IsFinite(radius) || radius <= 0d ||
            x - radius < shape.MinX - BoundaryEpsilon || x + radius > shape.MaxX + BoundaryEpsilon ||
            y - radius < shape.MinY - BoundaryEpsilon || y + radius > shape.MaxY + BoundaryEpsilon ||
            !ContainsPoint(shape, x, y))
            return false;

        var minimumDistanceSquared = radius * radius;
        for (int current = 0, previous = shape.Points.Count - 1;
             current < shape.Points.Count;
             previous = current++)
            if (DistanceToSegmentSquared(shape.Points[previous], shape.Points[current], x, y) +
                BoundaryEpsilon < minimumDistanceSquared)
                return false;
        return true;
    }

    private static double DistanceToSegmentSquared(
        HousingAreaShapePoint a, HousingAreaShapePoint b, double x, double y)
    {
        var deltaX = b.X - a.X;
        var deltaY = b.Y - a.Y;
        var lengthSquared = deltaX * deltaX + deltaY * deltaY;
        if (lengthSquared <= BoundaryEpsilon * BoundaryEpsilon)
        {
            var pointDeltaX = x - a.X;
            var pointDeltaY = y - a.Y;
            return pointDeltaX * pointDeltaX + pointDeltaY * pointDeltaY;
        }

        var projection = ((x - a.X) * deltaX + (y - a.Y) * deltaY) / lengthSquared;
        projection = Math.Clamp(projection, 0d, 1d);
        var nearestX = a.X + projection * deltaX;
        var nearestY = a.Y + projection * deltaY;
        var distanceX = x - nearestX;
        var distanceY = y - nearestY;
        return distanceX * distanceX + distanceY * distanceY;
    }

    private static bool IsOnSegment(HousingAreaShapePoint a, HousingAreaShapePoint b, double x, double y)
    {
        var cross = (x - a.X) * (b.Y - a.Y) - (y - a.Y) * (b.X - a.X);
        var length = Math.Max(1d, Math.Abs(b.X - a.X) + Math.Abs(b.Y - a.Y));
        if (Math.Abs(cross) > BoundaryEpsilon * length)
            return false;
        return x >= Math.Min(a.X, b.X) - BoundaryEpsilon &&
               x <= Math.Max(a.X, b.X) + BoundaryEpsilon &&
               y >= Math.Min(a.Y, b.Y) - BoundaryEpsilon &&
               y <= Math.Max(a.Y, b.Y) + BoundaryEpsilon;
    }

    private static bool HasFiniteBounds(HousingAreaShapeTemplate shape) =>
        IsFinite(shape.MinX) && IsFinite(shape.MinY) && IsFinite(shape.MaxX) && IsFinite(shape.MaxY);

    private static bool IsFinite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
}
