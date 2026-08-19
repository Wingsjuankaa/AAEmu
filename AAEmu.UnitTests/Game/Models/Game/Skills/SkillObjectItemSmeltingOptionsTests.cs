using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class SkillObjectItemSmeltingOptionsTests
{
    [Test]
    public async Task CapturedBody_ConsumesBoolAndRecipeIdBeforeInputDirection()
    {
        var stream = new PacketStream();
        stream.Write(false);
        stream.Write(0x12345678u);
        stream.Write((byte)0x5a);
        stream.Rollback();

        var options = new SkillObjectItemSmeltingOptions();
        options.Read(stream);

        await Assert.That(options.AutoUseAaPoint).IsFalse();
        await Assert.That(options.SmeltingDescriptionId).IsEqualTo(0x12345678u);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }

    [Test]
    public async Task StartedCastExtra_EchoesNativeType20Body()
    {
        var options = (SkillObjectItemSmeltingOptions)SkillObject.GetByType(
            SkillObjectType.ItemSmeltingOptions);
        options.AutoUseAaPoint = true;
        options.SmeltingDescriptionId = 32;

        var stream = new PacketStream();
        stream.WriteSkillCastExtra(options);
        var body = stream.GetBytes();

        await Assert.That(body.Length).IsEqualTo(7);
        await Assert.That(body[0]).IsEqualTo((byte)20);
        await Assert.That(body[1]).IsEqualTo((byte)1);
        await Assert.That(BitConverter.ToUInt32(body, 2)).IsEqualTo(32u);
        await Assert.That(body[6]).IsEqualTo((byte)0);
        await Assert.That(SkillObject.IsKnownType(20)).IsTrue();
    }
}
