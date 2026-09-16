using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectNoneTests
{
    [Test]
    [Arguments(0x00)]
    [Arguments(0x40)]
    [Arguments(0x80)]
    [Arguments(0xc0)]
    public async Task EmptyCastExtra_IsAccepted_AndLeavesInputDirection(int flag)
    {
        // Ordinary attacks and item casts need no SkillCastExtra body. The two
        // upper bits are independent flags, not extra type bits.
        var stream = new PacketStream();
        stream.Write((byte)flag);
        stream.Write((byte)0x5a);
        stream.Rollback();
        var type = stream.ReadByte() & 0x3f;
        await Assert.That(SkillObject.IsKnownType(type)).IsTrue();
        var extra = SkillObject.GetByType((SkillObjectType)type);
        var bodyStart = stream.Pos;
        extra.Read(stream);
        await Assert.That(extra.Flag).IsEqualTo(SkillObjectType.None);
        await Assert.That(stream.Pos).IsEqualTo(bodyStart);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.LeftBytes).IsEqualTo(0);
    }

    [Test]
    [Arguments(13)]
    [Arguments(31)]
    [Arguments(63)]
    public async Task UnknownExtraType_RemainsRejected(int type)
    {
        await Assert.That(SkillObject.IsKnownType(type)).IsFalse();
    }
}
