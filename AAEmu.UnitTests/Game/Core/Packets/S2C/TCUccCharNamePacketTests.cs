using System.Net;
using System.Net.Sockets;
using System.Reflection;
using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Network.Stream;
using AAEmu.Game.Core.Packets.C2S;
using AAEmu.Game.Core.Packets.S2C;

namespace AAEmu.UnitTests.Game.Core.Packets.S2C;

[NotInParallel]
public class TCUccCharNamePacketTests
{
    private static readonly FieldInfo NameInstance = typeof(Singleton<NameManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previousNames;
    private NameManager _names;

    [Before(Test)]
    public void Setup()
    {
        _previousNames = NameInstance.GetValue(null);
        _names = new NameManager();
        _names.Load([], [], []);
        _names.AddCharacter(1007, "Dannia", 1);
        NameInstance.SetValue(null, _names);
    }

    [After(Test)]
    public void Cleanup() => NameInstance.SetValue(null, _previousNames);

    [Test]
    public async Task CapturedPackOwnerRequestProducesNativeR575FrameOnEveryQuery()
    {
        // Request captured immediately before the 23:55:18 retail crash.
        var request = Convert.FromHexString("0A000900EF03000000000000");
        var session = new RecordingSession();
        var connection = new StreamConnection(session);
        var handler = new StreamProtocolHandler();
        handler.RegisterPacket(CTOffsets.CTUccCharacterNamePacket, typeof(CTUccCharacterNamePacket));

        for (var i = 0; i < 2; i++)
            handler.OnReceive(connection, request, 0, request.Length);

        await Assert.That(session.Packets.Count).IsEqualTo(2);
        foreach (var response in session.Packets)
        {
            // u16 length, u16 opcode 8, u64 owner, u16 UTF-8 byte count, name.
            await Assert.That(Convert.ToHexString(response))
                .IsEqualTo("12000800EF03000000000000060044616E6E6961");
        }
        await Assert.That(_names.GetCharacterName(1007)).IsEqualTo("Dannia");
        await Assert.That(connection.LastPacket).IsNull();
    }

    [Test]
    public async Task NativeBodyPreservesHighIdBitsAndUtf8NameBoundary()
    {
        var stream = new TCUccCharNamePacket(0x12345678000003EF, "Dueño").Encode();
        stream.Pos = 0;
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)18);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)8);
        await Assert.That(stream.ReadUInt64()).IsEqualTo(0x12345678000003EFUL);
        await Assert.That(stream.ReadString()).IsEqualTo("Dueño");
        await Assert.That(stream.HasBytes).IsFalse();
    }

    [Test]
    public async Task UnknownAndWideOwnerIdsCannotResolveToExistingLocalCharacter()
    {
        var session = new RecordingSession();
        var packet = new CTUccCharacterNamePacket { Connection = new StreamConnection(session) };
        foreach (var id in new ulong[] { 0, 1008, 0x1000003EF, ulong.MaxValue })
        {
            var body = new PacketStream();
            body.Write(id);
            body.Pos = 0;
            packet.Read(body);
            await Assert.That(body.HasBytes).IsFalse();
        }
        await Assert.That(session.Packets.Count).IsEqualTo(0);
        await Assert.That(_names.GetCharacterName(1007)).IsEqualTo("Dannia");
    }

    [Test]
    public async Task LegacyTruncatedAndOversizedRequestsDoNotSendOwnerNames()
    {
        var session = new RecordingSession();
        var packet = new CTUccCharacterNamePacket { Connection = new StreamConnection(session) };
        foreach (var hex in new[] { "", "EF030000", "EF030000000000", "EF0300000000000000" })
            packet.Read(new PacketStream(Convert.FromHexString(hex)));
        await Assert.That(session.Packets.Count).IsEqualTo(0);
    }

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
}
