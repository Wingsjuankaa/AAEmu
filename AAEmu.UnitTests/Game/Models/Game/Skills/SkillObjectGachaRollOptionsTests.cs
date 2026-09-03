using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectGachaRollOptionsTests
{
    [Test]
    public async Task Type16_RoundTripsFourByteCountBeforeInputDirection()
    {
        var written = (SkillObjectGachaRollOptions)SkillObject.GetByType(
            SkillObjectType.GachaRollOptions);
        written.Count = 10;

        var stream = new PacketStream();
        written.Write(stream);
        stream.Write((byte)0x5a);
        await Assert.That(stream.GetBytes()).IsEquivalentTo(
            new byte[] { 0x10, 0x0a, 0x00, 0x00, 0x00, 0x5a });
        stream.Rollback();

        var type = (SkillObjectType)(stream.ReadByte() & 0x3f);
        await Assert.That(SkillObject.IsKnownType((int)type)).IsTrue();
        var read = (SkillObjectGachaRollOptions)SkillObject.GetByType(type);
        read.Read(stream);

        await Assert.That(read.Count).IsEqualTo(10u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.LeftBytes).IsEqualTo(0);
    }
}
