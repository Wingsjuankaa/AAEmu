using System.Net;
using System.Net.Sockets;
using AAEmu.Commons.Network.Core;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class SquadLoginTests
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
    public async Task LoginWithoutSquad_ClearsQueueWithoutAnnouncingADisband_OnRepeatedLogin()
    {
        var session = new RecordingSession();
        var character = new Character(new AAEmu.Game.Models.Game.Units.UnitCustomModelParams()) { Id = 1007, Name = "Test" };
        character.Connection = new GameConnection(session) { ActiveChar = character };
        var manager = new SquadManager();

        manager.SyncClientSquadAfterLogin(character);
        manager.SyncClientSquadAfterLogin(character);

        await Assert.That(session.Packets.Count).IsEqualTo(2);
        foreach (var packet in session.Packets)
        {
            await Assert.That(BitConverter.ToUInt16(packet, 6)).IsEqualTo(SCOffsets.SCCancelInstantGamePacket);
            await Assert.That(BitConverter.ToUInt16(packet, 8)).IsEqualTo((ushort)0);
        }
    }
}
