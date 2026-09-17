using System.Net;
using System.Net.Sockets;
using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class FishSpotsTests
{
    private sealed class RecordingSession : ISession
    {
        public List<byte[]> Packets { get; } = [];
        public IPAddress Ip => IPAddress.Loopback;
        public uint SessionId => 1;
        public Socket Socket => null!;
        public void SendPacket(byte[] packet) => Packets.Add(packet);
        public void AddAttribute(string name, object attribute) { }
        public object GetAttribute(string name) => null;
        public void ClearAttribute(string name) { }
        public void Close() { }
    }

    [Test]
    public async Task OverrideSurvivesBuffRemoval_ThenRestoresLatestBuffRange()
    {
        var session = new RecordingSession();
        var player = new Character(new UnitCustomModelParams()) { Id = 1007 };
        player.Connection = new GameConnection(session) { ActiveChar = player };
        var entry = new TelescopeRegistrationEntry { Player = player, ShowFishSchoolRange = 1000f };
        entry.ShowAllFishSchools = true;
        entry.ShowAllFishSchools = true;
        entry.ShowFishSchoolRange = 0;
        await Assert.That(entry.IsActive).IsTrue();
        await Assert.That(session.Packets.Count).IsEqualTo(2);
        entry.ShowFishSchoolRange = 850f;
        entry.ShowAllFishSchools = false;
        await Assert.That(entry.EffectiveFishSchoolRange).IsEqualTo(850f);
        await Assert.That(session.Packets.Count).IsEqualTo(3);
        var restored = session.Packets[^1];
        await Assert.That(BitConverter.ToUInt16(restored, 6)).IsEqualTo(SCOffsets.SCSchoolOfFishFinderToggledPacket);
        await Assert.That(restored[8]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToSingle(restored, 9)).IsEqualTo(850f);
        entry.ShowFishSchoolRange = 0;
        await Assert.That(entry.IsActive).IsFalse();
        await Assert.That(session.Packets[^1][8]).IsEqualTo((byte)0);
    }

    [Test]
    public async Task WholeWorldIncludesDistantSchools_ButNeverOtherWorldsOrInstances()
    {
        var player = new Character(new UnitCustomModelParams());
        var near = School(1, 800f);
        var far = School(2, 40000f);
        var otherInstance = School(3, 50f);
        typeof(AAEmu.Game.Models.Game.World.Transform.Transform)
            .GetField("_instanceId", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)!
            .SetValue(otherInstance.Transform, unchecked(player.Transform.InstanceId + 1));
        var otherWorld = School(4, 50f);
        typeof(AAEmu.Game.Models.Game.World.Transform.Transform).GetProperty("WorldId")!
            .SetValue(otherWorld.Transform, player.Transform.WorldId + 1);
        var entry = new TelescopeRegistrationEntry { ShowFishSchoolRange = 1000f };
        entry.Player = player;
        List<Doodad> schools = [near, far, otherInstance, otherWorld];
        var ordinary = RadarManager.SelectFishSchools(entry, schools);
        await Assert.That(ordinary.Count).IsEqualTo(1);
        await Assert.That(ordinary[0].ObjId).IsEqualTo(near.ObjId);
        // Detach the player while toggling to avoid sending on a test-only character.
        entry.Player = null;
        entry.ShowAllFishSchools = true;
        entry.Player = player;
        var all = RadarManager.SelectFishSchools(entry, schools);
        await Assert.That(all.Count).IsEqualTo(2);
        await Assert.That(all.Contains(far)).IsTrue();
        entry.Player = null;
        entry.ShowAllFishSchools = false;
        entry.ShowFishSchoolRange = 0;
        entry.Player = player;
        await Assert.That(RadarManager.SelectFishSchools(entry, schools).Count).IsEqualTo(0);
    }

    [Test]
    [Arguments(0)]
    [Arguments(1)]
    [Arguments(10)]
    [Arguments(11)]
    [Arguments(21)]
    public async Task PacketBatchesHaveAtMostTenEntries_AndOneFinalMarker(int count)
    {
        var schools = Enumerable.Range(1, count).Select(i => School((uint)i, i * 50f)).ToList();
        var packets = RadarManager.FishSchoolPackets(schools).ToList();
        await Assert.That(packets.Count).IsEqualTo(Math.Max(1, (count + 9) / 10));
        var total = 0;
        for (var i = 0; i < packets.Count; i++)
        {
            var body = packets[i].Write(new PacketStream()).GetBytes();
            await Assert.That(body[0]).IsEqualTo((byte)(i == packets.Count - 1 ? 1 : 0));
            await Assert.That(body[1]).IsEqualTo((byte)Math.Min(10, count - total));
            total += body[1];
            if (count == 0)
                await Assert.That(body.Length).IsEqualTo(2);
        }
        await Assert.That(total).IsEqualTo(count);
    }

    private static Doodad School(uint id, float x)
    {
        var school = new Doodad { ObjId = id, Template = new DoodadTemplate { Id = 6447, GroupId = 65 } };
        school.Transform.Local.SetPosition(x, 0, 0, 0, 0, 0);
        return school;
    }
}
