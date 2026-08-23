using AAEmu.Game.Models.Game.World.Transform;

namespace AAEmu.Game.Models.Json;

/// <summary>
/// Declares that a bounded set of placements from one legacy spawn file is replaced by a
/// version-specific catalog. Other overlays remain eligible, so quest actors can still pin an
/// explicit phase while sharing the retail transform.
/// </summary>
public class JsonDoodadSpawnReplacement
{
    public string SourceFile { get; set; } = string.Empty;
    public string ReplacementFile { get; set; } = string.Empty;
    public float MinX { get; set; }
    public float MinY { get; set; }
    public float MaxX { get; set; }
    public float MaxY { get; set; }

    public bool Contains(WorldSpawnPosition position) =>
        position.X >= MinX && position.X < MaxX && position.Y >= MinY && position.Y < MaxY;
}
