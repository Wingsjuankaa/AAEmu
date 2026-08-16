using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Services.WebApi.Models;

namespace AAEmu.UnitTests.Game.Services.WebApi;

public class CharacterInventorySnapshotModelTests
{
    [Test]
    public async Task Create_MapsNativeEquipmentDetailWithoutExposingPersistence()
    {
        var template = new ItemTemplate { Id = 60000, Name = "Control Center Test Nodachi" };
        var item = new EquipItem(0x0102030405060708, template, 1)
        {
            SlotType = SlotType.Equipment,
            Slot = (int)EquipmentItemSlot.Mainhand,
            Grade = 12,
            ScaledA = 19,
            Durability = 145,
            GemData = new uint[EquipItem.GemDataSlots]
        };
        item.GemData[3] = 2800034;
        item.GemData[4] = 41001;

        var result = CharacterItemSnapshotModel.Create(item, true);

        await Assert.That(result.Id).IsEqualTo(0x0102030405060708UL);
        await Assert.That(result.TemplateId).IsEqualTo(60000u);
        await Assert.That(result.TemplateName).IsEqualTo("Control Center Test Nodachi");
        await Assert.That(result.SlotName).IsEqualTo("Mainhand");
        await Assert.That(result.TemperScaleId).IsEqualTo((ushort)19);
        await Assert.That(result.Durability).IsEqualTo((byte)145);
        await Assert.That(result.SocketAndSynthesisData).IsEquivalentTo(new uint[] { 2800034, 41001 });
    }
}
