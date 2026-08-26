using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCSkillStartedFailurePacketTests
{
    [Test]
    public async Task BagFullUsesFailedStartWithZeroTimelineAndNoCastTime()
    {
        var template = new SkillTemplate { Id = 40812, CastingTime = 1000 };
        var packet = new SCSkillStartedPacket(
            template.Id,
            0,
            new SkillCasterUnit(11),
            new SkillCastDoodadTarget
            {
                Type = SkillCastTargetType.Doodad,
                ObjId = 22
            },
            new Skill(template),
            new SkillObject())
        {
            RealCastTimeMs = 0,
            BaseCastTimeMs = 0
        };
        packet.SetSkillResult(SkillResult.BagFull);
        var stream = new PacketStream();

        packet.Write(stream);
        stream.Pos = 0;

        await Assert.That(stream.ReadUInt32()).IsEqualTo(template.Id);
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)0);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCasterType.Unit);
        await Assert.That(stream.ReadBc()).IsEqualTo(11u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillCastTargetType.Doodad);
        await Assert.That(stream.ReadBc()).IsEqualTo(22u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillObjectType.None);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0); // inputDirection
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)0); // real cast time / 10
        await Assert.That(stream.ReadUInt16()).IsEqualTo((ushort)0); // base cast time / 10
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0); // cast synergy
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)ExtraDataFlags.HasByte);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)SkillResult.BagFull);
        await Assert.That(stream.Pos).IsEqualTo(stream.Count);
    }
}
