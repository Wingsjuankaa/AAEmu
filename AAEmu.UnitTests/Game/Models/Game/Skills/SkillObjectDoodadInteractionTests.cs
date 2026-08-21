using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectDoodadInteractionTests
{
    [Test]
    public async Task Type28_RoundTripsEightByteBodyBeforeInputDirection()
    {
        var written = (SkillObjectDoodadInteraction)SkillObject.GetByType(
            SkillObjectType.DoodadInteraction);
        written.Value1 = 0x11223344;
        written.Value2 = 0x55667788;

        var stream = new PacketStream();
        written.Write(stream);
        stream.Write((byte)0x5a); // common CSStartSkill inputDirection
        await Assert.That(stream.GetBytes().Length).IsEqualTo(10);
        stream.Rollback();

        var type = (SkillObjectType)(stream.ReadByte() & 0x3f);
        await Assert.That(type).IsEqualTo(SkillObjectType.DoodadInteraction);
        var read = (SkillObjectDoodadInteraction)SkillObject.GetByType(type);
        read.Read(stream);

        await Assert.That(read.Value1).IsEqualTo(0x11223344u);
        await Assert.That(read.Value2).IsEqualTo(0x55667788u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }
}
