using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.UnitTests.Utils.Mocks;

namespace AAEmu.UnitTests.Game.Models.Game.Items.Containers;

public class ItemContainerCommittedTaskPacketTests
{
    [Test]
    public async Task FourSynthesisStackUpdates_AreFramedAsFourSingleTaskPackets()
    {
        var committed = new List<(ItemTask Task, ulong? RemovedId)>();
        for (uint id = 1; id <= 4; id++)
        {
            var item = new ItemMock(id, 19)
            {
                SlotType = SlotType.Inventory,
                Slot = (int)id - 1
            };
            committed.Add((new ItemCountUpdate(item, -1), null));
        }

        var packets = ItemContainer.BuildCommittedItemTaskPackets(
            ItemTaskType.GradeEnchant, committed);

        await Assert.That(packets.Count).IsEqualTo(4);
        foreach (var packet in packets)
        {
            var stream = new PacketStream();
            packet.Write(stream);
            var body = stream.GetBytes();

            // unitOwnerType, task reason, task count
            await Assert.That(body[2]).IsEqualTo((byte)1);
        }
    }

    [Test]
    public async Task RemovedItem_IsForcedOnlyByItsOwnPacket()
    {
        var removedWithoutForce = new ItemMock(1, 1) { SlotType = SlotType.Inventory, Slot = 0 };
        var removedWithForce = new ItemMock(2, 1) { SlotType = SlotType.Inventory, Slot = 1 };
        var packets = ItemContainer.BuildCommittedItemTaskPackets(
            ItemTaskType.GradeEnchant,
            [
                (new ItemRemoveSlot(removedWithoutForce), null),
                (new ItemRemoveSlot(removedWithForce), removedWithForce.Id)
            ]);

        var first = new PacketStream();
        packets[0].Write(first);
        var second = new PacketStream();
        packets[1].Write(second);

        // The first packet has no forced-removal id; the second packet is longer by that u64.
        await Assert.That(second.GetBytes().Length - first.GetBytes().Length).IsEqualTo(8);
    }
}
