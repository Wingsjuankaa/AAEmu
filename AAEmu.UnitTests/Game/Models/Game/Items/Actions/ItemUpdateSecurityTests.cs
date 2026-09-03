using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Actions;

public class ItemUpdateSecurityTests
{
    [Test]
    public async Task Write_EmitsExactR575UpdateFlagsBody()
    {
        var unlockTime = new DateTime(2026, 9, 3, 12, 0, 0, DateTimeKind.Utc);
        var item = new Item(0x1122334455667788,
            new ItemTemplate { Id = 200, MaxCount = 1 }, 1)
        {
            SlotType = SlotType.Inventory,
            Slot = 37,
            ItemFlags = ItemFlag.Secure | ItemFlag.Unpacked,
            UnsecureTime = unlockTime,
            UnpackTime = DateTime.MinValue
        };
        var task = new ItemUpdateSecurity(
            item,
            (byte)item.ItemFlags,
            isUnsecureExcess: false,
            isUnsecureSet: true,
            isUnpack: true,
            prevBits: (byte)ItemFlag.Secure);

        var bytes = task.Write(new PacketStream()).GetBytes();
        await Assert.That(bytes.Length).IsEqualTo(34);
        var body = new PacketStream(bytes);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)ItemAction.UpdateFlags);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)SlotType.Inventory);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)37);
        await Assert.That(body.ReadUInt64()).IsEqualTo(item.Id);
        await Assert.That(body.ReadByte()).IsEqualTo((byte)(ItemFlag.Secure | ItemFlag.Unpacked));
        await Assert.That(body.ReadByte()).IsEqualTo((byte)ItemFlag.Secure);
        await Assert.That(body.ReadBoolean()).IsFalse();
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadBoolean()).IsTrue();
        await Assert.That(body.ReadInt64()).IsEqualTo(new DateTimeOffset(unlockTime).ToUnixTimeSeconds());
        // The native empty-date sentinel is Unix 0.
        await Assert.That(body.ReadInt64()).IsEqualTo(0L);
    }
}
