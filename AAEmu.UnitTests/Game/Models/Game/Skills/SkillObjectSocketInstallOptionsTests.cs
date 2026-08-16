using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectSocketInstallOptionsTests
{
    [Test]
    public async Task CapturedDefaultInstallBody_ConsumesExactlySixBytes()
    {
        // The first broken r575 cast left these six bytes unread after skill-object flag 10.
        var stream = new PacketStream();
        stream.Write(true);
        stream.Write(0u);
        stream.Write(false);
        stream.Write((byte)0x5a); // common inputDirection follows the skill-object body
        stream.Rollback();

        var options = new SkillObjectSocketInstallOptions();
        options.Read(stream);

        await Assert.That(options.AutoUseAaPoint).IsTrue();
        await Assert.That(options.Count).IsEqualTo(0u);
        await Assert.That(options.Continuous).IsFalse();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }

    [Test]
    public async Task InstallOptions_RoundTripNativeLayout()
    {
        var written = (SkillObjectSocketInstallOptions)SkillObject.GetByType(
            SkillObjectType.SocketInstallOptions);
        written.AutoUseAaPoint = false;
        written.Count = 10;
        written.Continuous = true;

        var stream = new PacketStream();
        written.Write(stream);
        await Assert.That(stream.GetBytes().Length).IsEqualTo(7);
        stream.Rollback();

        await Assert.That((SkillObjectType)stream.ReadByte())
            .IsEqualTo(SkillObjectType.SocketInstallOptions);
        var read = new SkillObjectSocketInstallOptions();
        read.Read(stream);
        await Assert.That(read.AutoUseAaPoint).IsFalse();
        await Assert.That(read.Count).IsEqualTo(10u);
        await Assert.That(read.Continuous).IsTrue();
    }

    [Test]
    public async Task StartedCastExtra_EchoesCompleteSocketBodyBeforeInputDirection()
    {
        var options = (SkillObjectSocketInstallOptions)SkillObject.GetByType(
            SkillObjectType.SocketInstallOptions);
        options.AutoUseAaPoint = true;
        options.Count = 4;
        options.Continuous = true;

        var stream = new PacketStream();
        stream.WriteSkillCastExtra(options);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(8);
        await Assert.That(body[0]).IsEqualTo((byte)SkillObjectType.SocketInstallOptions);
        await Assert.That(body[1]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToUInt32(body, 2)).IsEqualTo(4u);
        await Assert.That(body[6]).IsEqualTo((byte)1);
        await Assert.That(body[7]).IsEqualTo((byte)0);
    }
}
