using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectEvolvingRerollOptionsTests
{
    [Test]
    public async Task TypeNine_RoundTripsTwoNativeUInt32Fields()
    {
        var written = (SkillObjectEvolvingRerollOptions)SkillObject.GetByType(
            SkillObjectType.EvolvingRerollOptions);
        written.ModifierIndex = 2;
        written.ChangeToGroupId = 3912;
        var stream = new PacketStream();

        written.Write(stream);
        var bytes = stream.GetBytes();
        stream.Rollback();

        await Assert.That(bytes.Length).IsEqualTo(9);
        await Assert.That((SkillObjectType)stream.ReadByte()).IsEqualTo(SkillObjectType.EvolvingRerollOptions);
        var read = new SkillObjectEvolvingRerollOptions();
        read.Read(stream);
        await Assert.That(read.ModifierIndex).IsEqualTo(2u);
        await Assert.That(read.ChangeToGroupId).IsEqualTo(3912u);
        await Assert.That(SkillObject.IsKnownType(9)).IsTrue();
    }

    [Test]
    public async Task StartedAndFiredExtra_EchoCompleteTypeNineBody()
    {
        var options = (SkillObjectEvolvingRerollOptions)SkillObject.GetByType(
            SkillObjectType.EvolvingRerollOptions);
        options.ModifierIndex = 1;
        options.ChangeToGroupId = 0;
        var stream = new PacketStream();

        stream.WriteSkillCastExtra(options);
        var bytes = stream.GetBytes();

        await Assert.That(bytes.Length).IsEqualTo(10);
        await Assert.That(bytes[0]).IsEqualTo((byte)SkillObjectType.EvolvingRerollOptions);
        await Assert.That(BitConverter.ToUInt32(bytes, 1)).IsEqualTo(1u);
        await Assert.That(BitConverter.ToUInt32(bytes, 5)).IsEqualTo(0u);
        await Assert.That(bytes[9]).IsEqualTo((byte)0); // inputDirection
    }
}
