using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCEquipmentActivationPacketTests
{
    [Test]
    public async Task UnitStateCharacterEquipment_UsesOccupiedSlotsAsActivationFlags()
    {
        var unit = new Unit();
        unit.Equipment.Items.Add(new Item { Slot = 19, TemplateId = 12345 });
        var stream = new PacketStream();

        EquipmentSerializer.Write(stream, unit, BaseUnitType.Character);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadUInt64()).IsEqualTo(1UL << 19);
        await Assert.That(body.ReadUInt32()).IsEqualTo(12345u);
        await Assert.That(body.ReadUInt64()).IsEqualTo(1UL << 19);
    }

    [Test]
    public async Task ItemTaskSuccess_UsesActiveCharactersFinalEquipmentMask()
    {
        var character = new Character(new UnitCustomModelParams());
        character.Equipment.Items.Add(new Item { Slot = 15, TemplateId = 54321 });
        var connection = new GameConnection(null) { ActiveChar = character };
        var packet = new SCItemTaskSuccessPacket(ItemTaskType.SwapItems, [], []);
        packet.Connection = connection;
        var stream = new PacketStream();

        packet.Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)ItemTaskType.SwapItems);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadInt64()).IsEqualTo(0L);
        await Assert.That(body.ReadInt32()).IsEqualTo(0);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.ReadUInt64()).IsEqualTo(1UL << 15);
    }

    [Test]
    public async Task ExplicitActivationPacket_IsBcUidFollowedByOneU64()
    {
        var unit = new Unit { ObjId = 0x010203 };
        unit.Equipment.Items.Add(new Item { Slot = 16, TemplateId = 1 });
        var packet = new SCUnitEquipmentsRndAttrUnitModifierAvtivateChangedPacket(unit);
        var stream = new PacketStream();

        packet.Write(stream);
        var body = new PacketStream(stream.GetBytes());

        await Assert.That(body.ReadBc()).IsEqualTo(0x010203u);
        await Assert.That(body.ReadUInt64()).IsEqualTo(1UL << 16);
    }
}
