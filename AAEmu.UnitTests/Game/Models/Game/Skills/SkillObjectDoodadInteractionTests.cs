using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;

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

    [Test]
    public async Task SkillStarted_EchoesType28BodyBeforeCastTimes()
    {
        var template = new SkillTemplate { Id = 11629, CastingTime = 3000 };
        var interaction = new SkillObjectDoodadInteraction
        {
            Flag = SkillObjectType.DoodadInteraction,
            Value1 = 0x11223344,
            Value2 = 0x55667788
        };
        var target = new SkillCastDoodadTarget
        {
            Type = SkillCastTargetType.Doodad,
            ObjId = 0x010203
        };
        var packet = new SCSkillStartedPacket(template.Id, 7,
            new SkillCasterUnit(0x040506), target, new Skill(template), interaction)
        {
            RealCastTimeMs = 3000,
            BaseCastTimeMs = 3000
        };
        var stream = new PacketStream();

        packet.Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadUInt32()).IsEqualTo(template.Id);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)7);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCasterType.Unit);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x040506u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCastTargetType.Doodad);
        await Assert.That(stream.ReadBc()).IsEqualTo(0x010203u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillObjectType.DoodadInteraction);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0x11223344u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0x55667788u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0); // inputDirection
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)300);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)300);
    }
}
