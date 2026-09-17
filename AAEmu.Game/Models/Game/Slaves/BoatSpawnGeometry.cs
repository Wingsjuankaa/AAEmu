using System.Numerics;
using AAEmu.Game.Models.Game.Models;

namespace AAEmu.Game.Models.Game.Slaves;

/// <summary>
/// Terrain clearance for the native slave bounding box. AA10 SlaveLocator constructs
/// center +/- size / 2 (dedicate RVA 0x737f80); mass_box_size is not hull clearance.
/// This samples terrain, not the native physics world's full object collision query.
/// </summary>
public static class BoatSpawnGeometry
{
    public static bool HasBounds(SlaveTemplate template) =>
        Finite(template.ObbCenter) && Finite(template.ObbSize) &&
        template.ObbSize.X > 0f && template.ObbSize.Y > 0f && template.ObbSize.Z > 0f;

    private static bool Finite(Vector3 value) =>
        float.IsFinite(value.X) && float.IsFinite(value.Y) && float.IsFinite(value.Z);

    public static float RequiredDepth(SlaveTemplate template, ShipModelV1 model, float plantOffsetZ)
    {
        if (HasBounds(template))
            return MathF.Max(0f, template.ObbSize.Z / 2f - template.ObbCenter.Z - plantOffsetZ);

        // Zero boxes require native temporary-model bounds (RVA 0x737f80). Until that
        // fallback is available in Game, preserve its prior conservative requirement.
        return model == null ? 5f : model.MassBoxSizeZ - model.MassCenterZ + 1f;
    }

    /// <summary>Sample edges and interior at no more than the heightmap's 2 m resolution.</summary>
    public static Vector2[] Footprint(SlaveTemplate template, float spawnYaw)
    {
        if (!HasBounds(template))
            return [];
        var nx = (int)MathF.Ceiling(template.ObbSize.X / 2f);
        var ny = (int)MathF.Ceiling(template.ObbSize.Y / 2f);
        var points = new Vector2[(nx + 1) * (ny + 1)];
        var rotation = Matrix3x2.CreateRotation(spawnYaw);
        var index = 0;
        for (var x = 0; x <= nx; x++)
        for (var y = 0; y <= ny; y++)
        {
            var local = new Vector2(
                template.ObbCenter.X + template.ObbSize.X * ((float)x / nx - 0.5f),
                template.ObbCenter.Y + template.ObbSize.Y * ((float)y / ny - 0.5f));
            points[index++] = Vector2.Transform(local, rotation);
        }
        return points;
    }

    public static bool ClearsTerrain(Vector3 position, float requiredDepth, Vector2[] footprint,
        Func<Vector3, (float Floor, float Surface)> sample)
    {
        foreach (var offset in footprint)
        {
            var terrain = sample(position + new Vector3(offset, 0f));
            // Require water under the whole box, including its offset and orientation.
            // A neighboring ocean plane must not validate a hull crossing a lake bank.
            if (!float.IsFinite(terrain.Floor) || !float.IsFinite(terrain.Surface) ||
                terrain.Floor <= 0f ||
                terrain.Floor >= MathF.Min(position.Z, terrain.Surface) - requiredDepth)
                return false;
        }
        return true;
    }
}
