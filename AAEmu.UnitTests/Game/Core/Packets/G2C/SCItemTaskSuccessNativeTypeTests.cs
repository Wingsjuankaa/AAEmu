using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCItemTaskSuccessNativeTypeTests
{
    // Independently extracted from the r575 client task-name table at RVA B5A010,
    // stride 0x28. Inherited AAEmu numbering emitted unrelated UI task events.
    [Test]
    [Arguments(ItemTaskType.QuestStart, 37)]
    [Arguments(ItemTaskType.QuestSupplyItems, 40)]
    [Arguments(ItemTaskType.SkillReagents, 42)]
    [Arguments(ItemTaskType.SkillEffectGainItem, 44)]
    [Arguments(ItemTaskType.Auction, 48)]
    [Arguments(ItemTaskType.Mail, 49)]
    [Arguments(ItemTaskType.Trade, 50)]
    [Arguments(ItemTaskType.EnchantPhysical, 52)]
    [Arguments(ItemTaskType.ItemLock, 92)]
    [Arguments(ItemTaskType.ItemUnlock, 93)]
    [Arguments(ItemTaskType.ItemUnlockExcess, 94)]
    [Arguments(ItemTaskType.GradeEnchant, 95)]
    [Arguments(ItemTaskType.Socketing, 99)]
    [Arguments(ItemTaskType.Evolving, 100)]
    [Arguments(ItemTaskType.Refurbishment, 127)]
    [Arguments(ItemTaskType.BlessUthstinInitStats, 153)]
    public async Task TaskByte_MatchesClientTable(ItemTaskType task, int nativeId)
    {
        var packet = new SCItemTaskSuccessPacket(task, new List<ItemTask>(), []);
        var stream = new PacketStream();
        packet.Write(stream);

        await Assert.That(stream.GetBytes()[1]).IsEqualTo((byte)nativeId);
    }
}
