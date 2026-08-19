using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectSocketExtractOptionsTests
{
    [Test]
    public async Task CapturedSingleExtractionBody_ConsumesExactlyFiveBytes()
    {
        // Live r575 capture: flag 11 followed by index=0, extractAll=false and inputDirection=0.
        var stream = new PacketStream();
        stream.Write(0u);
        stream.Write(false);
        stream.Write((byte)0);
        stream.Rollback();

        var options = new SkillObjectSocketExtractOptions();
        options.Read(stream);

        await Assert.That(options.SocketIndex).IsEqualTo(0u);
        await Assert.That(options.ExtractAll).IsFalse();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0);
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }

    [Test]
    public async Task ExtractionOptions_RoundTripNativeLayout()
    {
        var written = (SkillObjectSocketExtractOptions)SkillObject.GetByType(
            SkillObjectType.SocketExtractOptions);
        written.SocketIndex = 7;
        written.ExtractAll = true;

        var stream = new PacketStream();
        written.Write(stream);
        await Assert.That(stream.GetBytes().Length).IsEqualTo(6);
        stream.Rollback();

        await Assert.That((SkillObjectType)stream.ReadByte())
            .IsEqualTo(SkillObjectType.SocketExtractOptions);
        var read = new SkillObjectSocketExtractOptions();
        read.Read(stream);
        await Assert.That(read.SocketIndex).IsEqualTo(7u);
        await Assert.That(read.ExtractAll).IsTrue();
        await Assert.That(SkillObject.IsKnownType(11)).IsTrue();
    }

    [Test]
    public async Task StartedCastExtra_EchoesCompleteExtractionBodyBeforeInputDirection()
    {
        var options = (SkillObjectSocketExtractOptions)SkillObject.GetByType(
            SkillObjectType.SocketExtractOptions);
        options.SocketIndex = 3;
        options.ExtractAll = false;

        var stream = new PacketStream();
        stream.WriteSkillCastExtra(options);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(7);
        await Assert.That(body[0]).IsEqualTo((byte)SkillObjectType.SocketExtractOptions);
        await Assert.That(BitConverter.ToUInt32(body, 1)).IsEqualTo(3u);
        await Assert.That(body[5]).IsEqualTo((byte)0);
        await Assert.That(body[6]).IsEqualTo((byte)0);
    }
}
