using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectItemGradeEnchantingSupportTests
{
    [Test]
    public async Task NativeR575TypeSix_ReadsSupportBodyWithoutTrailingBytes()
    {
        var stream = new PacketStream();
        stream.Write(0x0102030405060708UL);
        stream.Write(true);
        stream.Pos = 0;

        var skillObject = SkillObject.GetByType((SkillObjectType)6);
        skillObject.Read(stream);

        var support = (SkillObjectItemGradeEnchantingSupport)skillObject;
        await Assert.That(SkillObject.IsKnownType(6)).IsTrue();
        await Assert.That(SkillObject.IsKnownType(7)).IsFalse();
        await Assert.That(support.Flag).IsEqualTo(SkillObjectType.ItemGradeEnchantingSupport);
        await Assert.That(support.SupportItemId).IsEqualTo(0x0102030405060708UL);
        await Assert.That(support.AutoUseAaPoint).IsTrue();
        await Assert.That(stream.Pos).IsEqualTo(stream.Count);
    }

    [Test]
    public async Task SkillStarted_EchoesCompleteTemperObjectBeforeCastTimes()
    {
        var template = new SkillTemplate { Id = 37723, CastingTime = 1500 };
        var support = new SkillObjectItemGradeEnchantingSupport
        {
            Flag = SkillObjectType.ItemGradeEnchantingSupport,
            SupportItemId = 0x0102030405060708UL,
            AutoUseAaPoint = true
        };
        var packet = new SCSkillStartedPacket(template.Id, 7,
            new SkillCasterUnit(11), new SkillCastUnitTarget(22), new Skill(template), support)
        {
            RealCastTimeMs = 1340,
            BaseCastTimeMs = 1500
        };
        var stream = new PacketStream();

        packet.Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadUInt32()).IsEqualTo(template.Id);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)7);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCasterType.Unit);
        await Assert.That(stream.ReadBc()).IsEqualTo(11u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCastTargetType.Unit);
        await Assert.That(stream.ReadBc()).IsEqualTo(22u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillObjectType.ItemGradeEnchantingSupport);
        await Assert.That(stream.ReadUInt64()).IsEqualTo(0x0102030405060708UL);
        await Assert.That(stream.ReadBoolean()).IsTrue();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0); // inputDirection
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)134);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)150);
    }
}
