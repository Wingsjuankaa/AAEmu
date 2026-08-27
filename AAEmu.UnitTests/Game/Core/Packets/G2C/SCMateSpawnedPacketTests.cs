using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCMateSpawnedPacketTests
{
    [Test]
    public async Task WritesExactR575MateIdentityAndTenSkillSlots()
    {
        var mate = new Mate
        {
            TlId = 0x1234,
            MateType = 2,
            Id = 0x01020304,
            ItemId = 0x0102030405060708,
            UserState = 3,
            Experience = 0x10203040,
            SpawnDelayTime = 0x50607080,
            Skills = [11, 22, 33]
        };
        var output = new PacketStream();

        new SCMateSpawnedPacket(mate).Write(output);
        var body = new PacketStream(output.GetBytes());

        await Assert.That(SCOffsets.SCMateSpawnedPacket).IsEqualTo((ushort)0x16A);
        await Assert.That(output.GetBytes()).Count().IsEqualTo(64);
        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)0x1234);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)2);
        await Assert.That(body.ReadUInt32()).IsEqualTo(0x01020304u);
        await Assert.That(body.ReadUInt64()).IsEqualTo(0x0102030405060708uL);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)3);
        await Assert.That(body.ReadUInt32()).IsEqualTo(0x10203040u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(0x50607080u);
        await Assert.That(Enumerable.Range(0, 10).Select(_ => body.ReadUInt32()).ToArray())
            .IsEquivalentTo(new uint[] { 11, 22, 33, 0, 0, 0, 0, 0, 0, 0 });
        await Assert.That(body.LeftBytes).IsEqualTo(0);
    }
}
