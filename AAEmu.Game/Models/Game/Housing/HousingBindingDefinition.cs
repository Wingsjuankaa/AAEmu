using System.Numerics;

using AAEmu.Game.Models.Game.DoodadObj.Static;
using AAEmu.Game.Models.Game.World.Transform;

using Newtonsoft.Json;

namespace AAEmu.Game.Models.Game.Housing;

public enum HousingInteractionBlockReason
{
    None = 0,
    MissingHousingTemplate,
    MissingDoodadTemplate,
    MissingModel,
    MissingPosition,
    InvalidTransform,
    MissingConsumer,
    TerritorialSubsystemRequired,
    CatalogMismatch,
    PendingWavePromotion
}

public enum HousingBindingPositionSource
{
    None = 0,
    Aa10ModelHelper
}

public sealed record HousingLocalTransform
{
    public float X { get; init; }
    public float Y { get; init; }
    public float Z { get; init; }
    public float RotationX { get; init; }
    public float RotationY { get; init; }
    public float RotationZ { get; init; }
    public float RotationW { get; init; } = 1f;
    public float ScaleX { get; init; } = 1f;
    public float ScaleY { get; init; } = 1f;
    public float ScaleZ { get; init; } = 1f;

    [JsonIgnore] public Vector3 Position => new(X, Y, Z);
    [JsonIgnore] public Quaternion Rotation => new(RotationX, RotationY, RotationZ, RotationW);
    [JsonIgnore] public Vector3 Scale => new(ScaleX, ScaleY, ScaleZ);

    [JsonIgnore]
    public bool IsFinite =>
        float.IsFinite(X) && float.IsFinite(Y) && float.IsFinite(Z) &&
        float.IsFinite(RotationX) && float.IsFinite(RotationY) &&
        float.IsFinite(RotationZ) && float.IsFinite(RotationW) &&
        float.IsFinite(ScaleX) && float.IsFinite(ScaleY) && float.IsFinite(ScaleZ) &&
        Rotation.LengthSquared() > 0f &&
        ScaleX > 0f && ScaleY > 0f && ScaleZ > 0f;

    public bool HasUniformScale(float tolerance = 0.0001f) =>
        MathF.Abs(ScaleX - ScaleY) <= tolerance &&
        MathF.Abs(ScaleX - ScaleZ) <= tolerance;

    public WorldSpawnPosition ToWorldSpawnPosition()
    {
        var euler = PositionAndRotation.FromQuaternion(Quaternion.Normalize(Rotation));
        return new WorldSpawnPosition
        {
            X = X,
            Y = Y,
            Z = Z,
            Roll = euler.X,
            Pitch = euler.Y,
            Yaw = euler.Z
        };
    }
}

public sealed record HousingBindingDefinition
{
    public uint HousingTemplateId { get; init; }
    public uint DoodadId { get; init; }
    public AttachPointKind AttachPointId { get; init; }
    public HousingLocalTransform Transform { get; init; }
    public bool ForceDbSave { get; init; }
    public HousingBindingPositionSource PositionSource { get; init; }
    public HousingInteractionBlockReason BlockReason { get; init; }

    [JsonIgnore]
    public bool IsExecutable =>
        BlockReason == HousingInteractionBlockReason.None &&
        PositionSource != HousingBindingPositionSource.None &&
        Transform is { IsFinite: true } &&
        Transform.HasUniformScale();
}
