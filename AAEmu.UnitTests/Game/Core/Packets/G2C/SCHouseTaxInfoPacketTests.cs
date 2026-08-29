using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Housing;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCHouseTaxInfoPacketTests
{
    [Test]
    public async Task NativeR575BodyWritesTaxStateInExactOrderAndWidths()
    {
        var due = new DateTime(2026, 9, 18, 15, 35, 5, DateTimeKind.Utc);
        var stream = new PacketStream();
        new SCHouseTaxInfoPacket(
            16, 1, 2, 300_000, 150_000, due,
            true, 0, 1, false, 1).Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt16()).IsEqualTo((ushort)16);
        await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(2u);
        await Assert.That(body.ReadUInt64()).IsEqualTo(300_000UL);
        await Assert.That(body.ReadUInt64()).IsEqualTo(150_000UL);
        await Assert.That(body.ReadInt64()).IsEqualTo(Helpers.UnixTime(due));
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)1);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.ReadByte()).IsEqualTo(HousingTaxState.TaxSealType);
        await Assert.That(body.HasBytes).IsFalse();
    }
}
