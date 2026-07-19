using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Units.Route;
using AAEmu.Game.Models.Game.World;

using System.Numerics;

using NLog;

namespace AAEmu.Game.Models.Game.NPChar;

public class NpcSpawnerNpc : Spawner<Npc>
{
    // ReSharper disable once InconsistentNaming
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();

    /// <summary>
    /// NpcSpawnerTemplateId
    /// </summary>
    public uint NpcSpawnerTemplateId { get; init; }
    /// <summary>
    /// NpcTemplateId
    /// </summary>
    public uint MemberId { get; set; }
    /// <summary>
    /// MemberType should be "Npc" here
    /// </summary>
    public string MemberType { get; set; }
    /// <summary>
    /// Spawn priority weight
    /// </summary>
    public float Weight { get; init; }

    public NpcSpawnerNpc()
    {
        //
    }

    /// <summary>
    /// Creates a new instance of NpcSpawnerNpcs with a Spawner template id (npc_spanwers)
    /// </summary>
    /// <param name="spawnerTemplateId"></param>
    public NpcSpawnerNpc(uint spawnerTemplateId)
    {
        NpcSpawnerTemplateId = spawnerTemplateId;
    }

    public NpcSpawnerNpc(uint spawnerTemplateId, uint npcTemplateId)
    {
        NpcSpawnerTemplateId = spawnerTemplateId;
        MemberId = npcTemplateId;
        MemberType = "Npc";
    }

    /// <summary>
    /// Spawns Npcs from a NpcSpawner
    /// </summary>
    /// <param name="npcSpawner"></param>
    /// <param name="ownerId"></param>
    /// <returns>List of newly spawned NPCs</returns>
    /// <exception cref="InvalidOperationException"></exception>
    public List<Npc> Spawn(NpcSpawner npcSpawner, uint ownerId = 0)
    {
        switch (MemberType)
        {
            case "Npc":
                return SpawnNpc(npcSpawner, ownerId);
            case "NpcGroup":
                return SpawnNpcGroup(npcSpawner, ownerId);
            default:
                throw new InvalidOperationException($"Tried spawning an unsupported line from NpcSpawnerNpc - Id: {Id}");
        }
    }

    /// <summary>
    /// Internal Spawn Npc function for Spawn
    /// </summary>
    /// <param name="npcSpawner"></param>
    /// <param name="ownerId"></param>
    /// <returns></returns>
    private List<Npc> SpawnNpc(NpcSpawner npcSpawner, uint ownerId = 0)
    {
        var npcs = new List<Npc>();
        var npc = NpcManager.Instance.Create(npcSpawner.ParentWorld, 0, MemberId);
        if (npc == null)
        {
            Logger.Warn($"Npc {MemberId}, from spawner Id {npcSpawner.Id} not exist at db. Spawner Position: {npcSpawner.Position}");
            return null;
        }

        npc.ParentWorld = npcSpawner.ParentWorld;
        npc.OwnerId = ownerId;

        npc.RegisterNpcEvents();

        Logger.Trace($"Spawn npc templateId {MemberId} objId {npc.ObjId} from spawnerId {NpcSpawnerTemplateId} at Position: {npcSpawner.Position}");

        if (!npc.CanFly)
        {
            // NPC spawn data can drift from the terrain. The heightmap is the
            // correct floor for ordinary ground NPCs, but it has no knowledge
            // of static structures such as docks and bridges. object.dat is the
            // authoritative source for those floors; BAI remains a fallback for
            // navigable structures that are not represented by a brush.
            var sourceZ = npcSpawner.Position.Z;
            var terrainZ = npcSpawner.ParentWorld.GetHeight(npcSpawner.Position.X, npcSpawner.Position.Y);
            const float heightMismatchThreshold = 1.0f;
            var hasHeightMismatch = terrainZ != 0f &&
                                    MathF.Abs(sourceZ - terrainZ) > heightMismatchThreshold;
            var structuralFloorZ = 0f;
            var spawnPosition = new Vector3(npcSpawner.Position.X, npcSpawner.Position.Y, sourceZ);
            var keepStructuralHeight = hasHeightMismatch &&
                                       npcSpawner.ParentWorld.Template.TryGetStructuralSurfaceHeight(
                                           spawnPosition, out structuralFloorZ);

            if (hasHeightMismatch && !keepStructuralHeight)
                keepStructuralHeight = HasMatchingElevatedNavigationFloor(
                    npcSpawner, terrainZ, out structuralFloorZ);

            npc.UsesStructuralFloor = keepStructuralHeight;
            npc.StructuralFloorOffset = keepStructuralHeight ? sourceZ - structuralFloorZ : 0f;

            if (hasHeightMismatch && !keepStructuralHeight)
                npcSpawner.Position.Z = terrainZ;
        }

        npc.Spawner = npcSpawner;
        npc.Transform.ApplyWorldSpawnPosition(npcSpawner.Position);
        if (npc.Transform == null)
        {
            Logger.Error($"Can't spawn npc {MemberId} from spawnerId {NpcSpawnerTemplateId}. Transform is null.");
            return null;
        }

        npc.Transform.InstanceId = npc.Transform.InstanceId;

        if (npc.Ai != null)
        {
            npc.Ai.HomePosition = npc.Transform.World.Position;
            npc.Ai.IdlePosition = npc.Ai.HomePosition;
            npc.Ai.GoToSpawn();
        }

        npc.Spawner.RespawnTime = (int)Random.Shared.Next(npc.Spawner.Template.SpawnDelayMin, npc.Spawner.Template.SpawnDelayMax);
        npc.Spawn();

        var world = WorldManager.Instance.GetWorld(npc.Transform.InstanceId);
        world.Events.OnUnitSpawn(world, new OnUnitSpawnArgs { Npc = npc });
        npc.Simulation = new Simulation(npc);

        if (npc.Ai != null && !string.IsNullOrWhiteSpace(npcSpawner.FollowPath))
        {
            if (!npc.Ai.LoadAiPathPoints(npcSpawner.FollowPath, false))
                Logger.Warn($"Failed to load {npcSpawner.FollowPath} for NPC {npc.TemplateId} ({npc.ObjId})");
        }

        npcs.Add(npc);
        return npcs;
    }

    private static bool HasMatchingElevatedNavigationFloor(NpcSpawner npcSpawner, float terrainZ, out float navFloorZ)
    {
        var spawnPosition = new Vector3(npcSpawner.Position.X, npcSpawner.Position.Y, npcSpawner.Position.Z);
        // GeoData checks both NetMission and VertexMission information. The
        // earlier direct NetMission lookup missed static floor data used by
        // docks, bridges and similar world structures.
        navFloorZ = npcSpawner.ParentWorld.Template.GeoData?.GetHeight(spawnPosition, ensureBaiLoaded: true) ?? 0f;
        if (navFloorZ == 0f)
            return false;

        const float maxHeightDifference = 1.5f;
        const float minElevatedFloorDifference = 1.5f;

        return MathF.Abs(navFloorZ - spawnPosition.Z) <= maxHeightDifference &&
               navFloorZ - terrainZ >= minElevatedFloorDifference;
    }

    /// <summary>
    /// Internal Spawn NpcGroup function for Spawn
    /// </summary>
    /// <param name="npcSpawner"></param>
    /// <param name="ownerId"></param>
    /// <returns></returns>
    private List<Npc> SpawnNpcGroup(NpcSpawner npcSpawner, uint ownerId = 0)
    {
        return SpawnNpc(npcSpawner, ownerId);
    }
}
