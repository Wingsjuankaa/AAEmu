using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class EquipItemSocketLayoutTests
{
    [Test]
    public async Task NativeSockets_UseOnlyGemDataFourThroughTwelve()
    {
        var item = NewEquipment();
        item.GemData[3] = 987654; // synthesis XP
        item.GemData[13] = 81; // first synthesis-effect group
        item.IsDirty = false;

        for (var index = 0; index < EquipItem.NativeSocketCapacity; index++)
            await Assert.That(item.SetNativeSocket(index, (uint)(43500 + index))).IsTrue();

        await Assert.That(item.NativeSocketItemIds.ToArray())
            .IsEquivalentTo(Enumerable.Range(43500, 9).Select(value => (uint)value).ToArray());
        await Assert.That(item.GemData[3]).IsEqualTo(987654u);
        await Assert.That(item.GemData[13]).IsEqualTo(81u);
        await Assert.That(item.IsDirty).IsTrue();
        await Assert.That(item.SetNativeSocket(EquipItem.NativeSocketCapacity, 1)).IsFalse();
    }

    [Test]
    public async Task EquipmentDetail_RoundTripsEveryNativeSocket()
    {
        var written = NewEquipment();
        written.EvolvingExp = 321;
        written.RndAttrGroupIds = [81u, 82u, 83u];
        for (var index = 0; index < EquipItem.NativeSocketCapacity; index++)
            written.SetNativeSocket(index, (uint)(50000 + index));

        var stream = new PacketStream();
        written.WriteDetails(stream);
        stream.Rollback();

        var read = NewEquipment();
        read.ReadDetails(stream);

        await Assert.That(read.NativeSocketItemIds.ToArray())
            .IsEquivalentTo(written.NativeSocketItemIds.ToArray());
        await Assert.That(read.EvolvingExp).IsEqualTo(321);
        await Assert.That(read.RndAttrGroupIds.ToArray()).IsEquivalentTo([81u, 82u, 83u]);
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }

    private static EquipItem NewEquipment()
    {
        var template = new WeaponTemplate
        {
            Id = 60000,
            Level = 55,
            HoldableTemplate = new Holdable { SlotTypeId = 4 }
        };
        return new EquipItem(1, template, 1) { Grade = 12 };
    }
}
