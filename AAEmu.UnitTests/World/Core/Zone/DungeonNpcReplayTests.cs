using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using AAEmu.Commons.Network.Core;
using AAEmu.Commons.Utils;
using AAEmu.Game;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.World;
using AAEmu.World.Core.Network;
using AAEmu.World.Core.Relay;
using AAEmu.World.Core.Zone;

namespace AAEmu.UnitTests.World.Core.Zone;

[NotInParallel]
public class DungeonNpcReplayTests
{
    private readonly List<(FieldInfo Field, object Value)> _saved = [];
    private readonly List<uint> _replayed = [];
    private ConcurrentDictionary<uint, WorldInstance> _worlds;
    private WorldTemplate _template;
    private Func<uint, uint, uint, uint, float, float, float, float, float, bool> _oldMirror;

    private sealed class Session(uint id) : ISession
    {
        public IPAddress Ip => IPAddress.Loopback;
        public uint SessionId => id;
        public Socket Socket => null;
        public void SendPacket(byte[] packet) { }
        public void AddAttribute(string name, object attribute) { }
        public object GetAttribute(string name) => null;
        public void ClearAttribute(string name) { }
        public void Close() { }
    }

    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
        _saved.Add((field, field.GetValue(null)));
        field.SetValue(null, value);
    }

    [Before(Test)]
    public void Setup()
    {
        var manager = new WorldManager(null, null, null, null, null);
        _template = new WorldTemplate { Id = 59, Name = "instance_phantom_of_delphinad", ZoneKeys = [384] };
        manager.WorldTemplates[_template.Name] = _template;
        manager.MainWorld = new WorldInstance(new WorldTemplate { Id = 0, Name = "main_world" }, 0, true, 0);
        var flags = BindingFlags.NonPublic | BindingFlags.Instance;
        typeof(WorldManager).GetProperty("WorldNames", flags)!.SetValue(manager,
            Enumerable.Repeat("unused", 59).Append(_template.Name).ToList());
        typeof(WorldManager).GetField("_worldIdByZoneKey", flags)!.SetValue(manager,
            new Dictionary<uint, uint> { [384] = 59 });
        _worlds = new ConcurrentDictionary<uint, WorldInstance>();
        typeof(WorldManager).GetField("_worlds", flags)!.SetValue(manager, _worlds);
        Swap(manager);
        Swap(new ZoneSession());
        _oldMirror = WorldIntegration.OnZoneNpcSpawn;
        WorldIntegration.OnZoneNpcSpawn = (_, _, bc, _, _, _, _, _, _) =>
        {
            _replayed.Add(bc);
            return false; // Keep the native record pending; no fake NPC state on the wire.
        };
    }

    [After(Test)]
    public void Cleanup()
    {
        WorldIntegration.OnZoneNpcSpawn = _oldMirror;
        foreach (var (field, value) in _saved) field.SetValue(null, value);
    }

    private WorldInstance World(uint id)
    {
        var world = new WorldInstance(_template, 0, true, id);
        _worlds[id] = world;
        return world;
    }

    private static ZoneConnection Host(uint id, uint copy, ZoneConnectionState state = ZoneConnectionState.ZoneLoaded)
    {
        var host = new ZoneConnection(new Session(id)) { ZoneId = 384, InstanceId = copy, State = state };
        var raw = new byte[ZwSpawnNpcParser.MinBodyLength];
        BinaryPrimitives.WriteUInt32LittleEndian(raw.AsSpan(12), 20030);
        host.Units.RegisterWithId(id, raw);
        ZoneSession.Instance.Add(host);
        ZoneSession.Instance.IndexByZoneId(host);
        return host;
    }

    [Test]
    public async Task ManualHostBeforeWorld_ReplaysRetainedNpcAfterWorldCreation()
    {
        var host = Host(394, 0);
        await Assert.That(WorldIntegration.ResolveWorldForZone(384, 0)).IsNull();
        var world = World(100);
        NpcSpawnRelay.RemirrorDungeon(world);
        await Assert.That(_replayed.SequenceEqual(new uint[] { 394 })).IsTrue();
        await Assert.That(host.Units.Contains(394)).IsTrue();
        await Assert.That(host.Units.Count).IsEqualTo(1);
        await Assert.That(host.InstanceId).IsEqualTo(0u);
    }

    [Test]
    public async Task ExactCopy_ReplaysOnlyItsOwnHost()
    {
        var world = World(100);
        World(101);
        Host(394, 100);
        Host(395, 101);
        NpcSpawnRelay.RemirrorDungeon(world);
        await Assert.That(_replayed.SequenceEqual(new uint[] { 394 })).IsTrue();
    }

    [Test]
    public async Task AmbiguousManualHost_DoesNotPopulateEitherCopy()
    {
        var first = World(100);
        var second = World(101);
        Host(394, 0);
        NpcSpawnRelay.RemirrorDungeon(first);
        NpcSpawnRelay.RemirrorDungeon(second);
        await Assert.That(_replayed.Count).IsEqualTo(0);
    }

    [Test]
    public async Task JoinedHost_WaitsForZoneLoaded()
    {
        var world = World(100);
        var host = Host(394, 100, ZoneConnectionState.Joined);
        NpcSpawnRelay.RemirrorDungeon(world);
        await Assert.That(_replayed.Count).IsEqualTo(0);
        host.State = ZoneConnectionState.ZoneLoaded;
        NpcSpawnRelay.RemirrorDungeon(world);
        await Assert.That(_replayed.Count).IsEqualTo(1);
    }
}
