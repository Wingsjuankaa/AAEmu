using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

public class CSItemSecurityPacketTests
{
    [Test]
    [Arguments(true)]
    [Arguments(false)]
    public async Task SingleItemPacket_ReadsExactTenByteR575Body(bool secure)
    {
        const ulong itemId = 0x1122334455667788;
        var body = new PacketStream()
            .Write((byte)SlotType.Inventory)
            .Write((byte)37)
            .Write(itemId)
            .GetBytes();
        await Assert.That(body.Length).IsEqualTo(10);

        if (secure)
        {
            var packet = new CSItemSecurePacket();
            packet.Read(new PacketStream(body));
            await Assert.That(packet.SlotType).IsEqualTo(SlotType.Inventory);
            await Assert.That(packet.Slot).IsEqualTo((byte)37);
            await Assert.That(packet.ItemId).IsEqualTo(itemId);
        }
        else
        {
            var packet = new CSItemUnsecurePacket();
            packet.Read(new PacketStream(body));
            await Assert.That(packet.SlotType).IsEqualTo(SlotType.Inventory);
            await Assert.That(packet.Slot).IsEqualTo((byte)37);
            await Assert.That(packet.ItemId).IsEqualTo(itemId);
        }
    }

    [Test]
    public async Task EquipmentPackets_AcceptTheExactEmptyBody()
    {
        var body = new PacketStream(Array.Empty<byte>());
        new CSEquipmentsSecurePacket().Read(body);
        new CSEquipmentsUnsecurePacket().Read(new PacketStream(Array.Empty<byte>()));

        await Assert.That(body.GetBytes()).IsEmpty();
    }
}
