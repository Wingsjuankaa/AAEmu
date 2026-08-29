using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectHousingRebuildingTests
{
    [Test]
    public async Task Type7RoundTripsOneU32BeforeInputDirection()
    {
        var written = (SkillObjectHousingRebuilding)SkillObject.GetByType(
            SkillObjectType.HousingRebuilding);
        written.TargetHousingId = 0x11223344;

        var stream = new PacketStream();
        written.Write(stream);
        stream.Write((byte)0x5a);
        await Assert.That(stream.GetBytes().Length).IsEqualTo(6);
        stream.Pos = 0;

        var type = (SkillObjectType)(stream.ReadByte() & 0x3f);
        await Assert.That(type).IsEqualTo(SkillObjectType.HousingRebuilding);
        var read = (SkillObjectHousingRebuilding)SkillObject.GetByType(type);
        read.Read(stream);

        await Assert.That(read.TargetHousingId).IsEqualTo(0x11223344u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.HasBytes).IsFalse();
    }
}
