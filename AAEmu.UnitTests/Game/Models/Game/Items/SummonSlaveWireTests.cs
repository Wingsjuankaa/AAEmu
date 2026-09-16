using System.Buffers.Binary;
using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class SummonSlaveWireTests
{
    [Test]
    public async Task LiveUpdatePreservesSlaveFieldsInsteadOfClearingTheSummonLink()
    {
        var item = new SummonSlave { SlaveDbId = 578, IsDestroyed = 1, DetailTail = 50000 };
        var stream = new PacketStream();
        item.WriteUpdateDetailBlock(stream);
        var bytes = stream.GetBytes();
        await Assert.That(bytes.Length).IsEqualTo(128);
        await Assert.That(bytes[0]).IsEqualTo((byte)2);
        await Assert.That(BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(1))).IsEqualTo(578u);
        await Assert.That(bytes[5]).IsEqualTo((byte)1);
        await Assert.That(BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(30))).IsEqualTo(50000u);
        await Assert.That(bytes.AsSpan(34).ToArray()).IsEquivalentTo(new byte[94]);
    }

    [Test]
    public async Task LiveFishUpdateKeepsWeightAndLength()
    {
        var fish = new BigFish { Weight = 12.5f, Length = 140.75f, DetailQword = 12345 };
        var stream = new PacketStream();
        fish.WriteUpdateDetailBlock(stream);
        var bytes = stream.GetBytes();
        await Assert.That(bytes[0]).IsEqualTo((byte)6);
        await Assert.That(BitConverter.ToSingle(bytes, 1)).IsEqualTo(12.5f);
        await Assert.That(BitConverter.ToSingle(bytes, 5)).IsEqualTo(140.75f);
        await Assert.That(BinaryPrimitives.ReadInt64LittleEndian(bytes.AsSpan(9))).IsEqualTo(12345L);
        await Assert.That(bytes.Length).IsEqualTo(128);
    }

    [Test]
    public async Task NativeSnapshotHasFixedBodyAndFullDatabaseId()
    {
        var item = new SummonSlave { SlaveDbId = 0x12345602, DetailTail = 0x11223344 };
        var stream = new PacketStream();
        item.WriteDetails(stream);
        var bytes = stream.GetBytes();
        await Assert.That(bytes.Length).IsEqualTo(33);
        await Assert.That(Convert.ToHexString(bytes))
            .IsEqualTo("025634120000000000000000000000000000000000000000000000000044332211");
    }

    [Test]
    public async Task RepairTimestampDoesNotChangeSnapshotLengthOrConsumeNextField()
    {
        var time = new DateTime(2026, 9, 16, 12, 34, 56, DateTimeKind.Utc);
        var item = new SummonSlave { SlaveDbId = 578, RepairStartTime = time, IsDestroyed = 1 };
        var writer = new PacketStream();
        item.WriteDetails(writer);
        writer.Write(0x76543210u);
        var bytes = writer.GetBytes();
        await Assert.That(bytes.Length).IsEqualTo(37);
        await Assert.That(BinaryPrimitives.ReadInt64LittleEndian(bytes.AsSpan(5)))
            .IsEqualTo(new DateTimeOffset(time).ToUnixTimeSeconds());
        var reader = new PacketStream(bytes);
        var restored = new SummonSlave();
        restored.ReadDetails(reader);
        await Assert.That(restored.RepairStartTime).IsEqualTo(time);
        await Assert.That(restored.IsDestroyed).IsEqualTo((byte)1);
        await Assert.That(reader.ReadUInt32()).IsEqualTo(0x76543210u);
    }

    [Test]
    [Arguments(false)]
    [Arguments(true)]
    public async Task LegacyStorageMigratesOnceAndPreservesRepairState(bool repairing)
    {
        var time = new DateTime(2026, 9, 16, 12, 0, 0, DateTimeKind.Utc);
        var legacy = new PacketStream();
        legacy.Write((byte)2);
        legacy.WriteBc(0x123456u);
        legacy.Write((byte)1);
        if (repairing)
            legacy.Write(time);
        else
            legacy.Write(0);
        legacy.Write(new byte[24]);
        var item = new SummonSlave();
        item.ReadPersistentDetails(new PacketStream(legacy.GetBytes()));
        for (var round = 0; round < 3; round++)
        {
            await Assert.That(item.SlaveDbId).IsEqualTo(0x123456u);
            await Assert.That(item.IsDestroyed).IsEqualTo((byte)1);
            await Assert.That(item.RepairStartTime).IsEqualTo(repairing ? time : DateTime.MinValue);
            var saved = new PacketStream();
            item.WritePersistentDetails(saved);
            await Assert.That(saved.GetBytes().Length).IsEqualTo(37);
            item = new SummonSlave();
            item.ReadPersistentDetails(new PacketStream(saved.GetBytes()));
        }
    }

    [Test]
    public async Task NewStorageDoesNotMisidentifyIdsEndingInLegacyDiscriminator()
    {
        var item = new SummonSlave { SlaveDbId = 0x87654302, DetailTail = 987 };
        var writer = new PacketStream();
        item.WritePersistentDetails(writer);
        var restored = new SummonSlave();
        restored.ReadPersistentDetails(new PacketStream(writer.GetBytes()));
        await Assert.That(restored.SlaveDbId).IsEqualTo(item.SlaveDbId);
        await Assert.That(restored.DetailTail).IsEqualTo(987u);
        await Assert.That(restored.RepairStartTime).IsEqualTo(DateTime.MinValue);
    }

    [Test]
    public async Task FreshLegacyScrollHasNoSummonOrRepairState()
    {
        var item = new SummonSlave();
        item.ReadPersistentDetails(new PacketStream(new byte[33]));
        var writer = new PacketStream();
        item.WriteDetails(writer);
        await Assert.That(writer.GetBytes()).IsEquivalentTo(new byte[33]);
    }
}
