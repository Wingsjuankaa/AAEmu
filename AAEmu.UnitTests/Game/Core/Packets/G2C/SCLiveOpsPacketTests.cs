using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.ArchePass;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCLiveOpsPacketTests
{
    [Test]
    public async Task ArchePassPremiumUpgrade_WritesNativeReasonSevenAndPreservesCompletedNormalTrack()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(19, 183840, (byte)ArchePassStatus.Progress, true, 33, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.UpgradePremium, 0, false).Write(stream);
        await Assert.That(stream.GetBytes().SequenceEqual(Convert.FromHexString(
            "13000000210000000000000020CE0200000000000102070000000000"))).IsTrue();
    }

    [Test]
    public async Task ArchePassNormalRewardUpdate_WritesClaimedFrontierBeforeNativeReasonTwo()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(19, 7000, (byte)ArchePassStatus.Progress, false, 1, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.UpdateRewardItem, 0, false).Write(stream);
        await Assert.That(stream.GetBytes().SequenceEqual(Convert.FromHexString(
            "130000000100000000000000581B0000000000000002020000000000"))).IsTrue();
    }

    [Test]
    public async Task ArchePassPremiumRewardUpdate_PreservesTheSeparateNormalFrontier()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(19, 7000, (byte)ArchePassStatus.Progress, true, 2, 1);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.UpdateRewardItem, 0, false).Write(stream);
        await Assert.That(stream.GetBytes().SequenceEqual(Convert.FromHexString(
            "130000000200000001000000581B0000000000000102020000000000"))).IsTrue();
    }

    [Test]
    public async Task ArchePassPointUpdate_WritesNativeReasonOneAndAppliedDelta()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(88, 4500, (byte)ArchePassStatus.Progress, false, 0, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.UpdatePoint, 1000, false).Write(stream);
        await Assert.That(stream.GetBytes().SequenceEqual(Convert.FromHexString(
            "5800000000000000000000009411000000000000000201E803000000"))).IsTrue();
    }

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
    public async Task ArchePassState_WritesTheNativeWireFieldOrder()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(102, 1234, 2, true, 7, 8);
        new SCArchePassesPacket([state], true).Write(stream);
        await Assert.That(stream.GetBytes()).IsEquivalentTo(Convert.FromHexString(
            "0100000001660000000700000008000000D2040000000000000102"));
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadInt32()).IsEqualTo(1);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadInt32()).IsEqualTo(102);
        await Assert.That(body.ReadInt32()).IsEqualTo(7);
        await Assert.That(body.ReadInt32()).IsEqualTo(8);
        await Assert.That(body.ReadInt64()).IsEqualTo(1234);
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadByte()).IsEqualTo((byte)2);
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ArchePassBuyUpdate_WritesNativeReasonSixAfterState()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(48, 0, (byte)ArchePassStatus.Owned, false, 0, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.Buy, 0, false).Write(stream);
        await Assert.That(stream.GetBytes()).IsEquivalentTo(Convert.FromHexString(
            "30000000000000000000000000000000000000000001060000000000"));
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadInt32()).IsEqualTo(48);
        await Assert.That(body.ReadInt32()).IsEqualTo(0);
        await Assert.That(body.ReadInt32()).IsEqualTo(0);
        await Assert.That(body.ReadInt64()).IsEqualTo(0);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.ReadByte()).IsEqualTo((byte)ArchePassStatus.Owned);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)ArchePassUpdateReason.Buy);
        await Assert.That(body.ReadInt32()).IsEqualTo(0);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.Pos).IsEqualTo(body.Count);
    }

    [Test]
    public async Task ArchePassStartUpdate_WritesProgressStateAndNativeReasonFour()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(88, 0, (byte)ArchePassStatus.Progress, false, 0, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.Started, 0, false).Write(stream);

        await Assert.That(stream.GetBytes()).IsEquivalentTo(Convert.FromHexString(
            "58000000000000000000000000000000000000000002040000000000"));
    }

    [Test]
    public async Task ArchePassPauseUpdate_WritesOwnedStateBeforeAReplacementStarts()
    {
        var stream = new PacketStream();
        var state = new ArchePassWireState(88, 3500, (byte)ArchePassStatus.Owned, false, 0, 0);
        new SCUpdateArchePassPacket(state, ArchePassUpdateReason.Owned, 0, false).Write(stream);

        await Assert.That(stream.GetBytes()).IsEquivalentTo(Convert.FromHexString(
            "580000000000000000000000AC0D0000000000000001050000000000"));
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
