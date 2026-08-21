using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCLiveOpsPacketTests
{
    [Test]
    public async Task AccountAttendance_WritesExactlyThirtyOneFixedEntries()
    {
        var times = Enumerable.Range(1, SCAccountAttendancePacket.Days).Select(value => (long)value).ToArray();
        var archelife = Enumerable.Range(0, SCAccountAttendancePacket.Days).Select(value => value % 2 == 0).ToArray();
        var stream = new PacketStream();

        new SCAccountAttendancePacket(times, archelife).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        for (var index = 0; index < SCAccountAttendancePacket.Days; index++)
        {
            await Assert.That(body.ReadInt64()).IsEqualTo(times[index]);
            await Assert.That(body.ReadBoolean()).IsEqualTo(archelife[index]);
        }
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task AccountAttendance_RejectsNonNativeArrayLengths()
    {
        await Assert.That(() => new SCAccountAttendancePacket(new long[30], new bool[31]))
            .Throws<ArgumentException>();
    }

    [Test]
    public async Task EmptyArchePassInitialState_IsCountThenLastFlag()
    {
        var stream = new PacketStream();
        new SCArchePassesPacket([], true).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadInt32()).IsEqualTo(0);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ArchePassState_WritesTheNativeAlignedRecordFields()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(102, 1234, 2, true, 7, 8);
        new SCArchePassesPacket([state], true).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadInt32()).IsEqualTo(1);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadInt32()).IsEqualTo(102);
        await Assert.That(body.ReadInt64()).IsEqualTo(1234);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)2);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadInt32()).IsEqualTo(7);
        await Assert.That(body.ReadInt32()).IsEqualTo(8);
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ArchePassState_RejectsPagesAboveTheNativeTenRecordLimit()
    {
        var states = Enumerable.Range(1, 11)
            .Select(type => new ArchePassWireState(type, 0, 1, false, 0, 0))
            .ToArray();

        await Assert.That(() => new SCArchePassesPacket(states, true).Write(new PacketStream()))
            .Throws<InvalidOperationException>();
    }
}
