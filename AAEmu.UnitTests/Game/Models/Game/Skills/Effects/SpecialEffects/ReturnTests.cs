using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Effects.SpecialEffects;

public class ReturnTests
{
    [Test]
    public async Task MainWorldLoadPacket_WritesZeroInstanceBeforeZone()
    {
        var stream = new PacketStream();
        new SCLoadInstancePacket(
            0,
            149,
            12_279.8f,
            12_112.6f,
            140.2f,
            0,
            0,
            0.736_528f).Write(stream);

        var body = new PacketStream(stream.GetBytes());
        await Assert.That(body.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(body.ReadUInt32()).IsEqualTo(149u);
        await Assert.That(body.ReadSingle()).IsEqualTo(12_279.8f);
        await Assert.That(body.ReadSingle()).IsEqualTo(12_112.6f);
        await Assert.That(body.ReadSingle()).IsEqualTo(140.2f);
    }

    [Test]
    public async Task MainWorldReturn_UsesTeleportOnlyWhenAlreadyInMainWorldInstance()
    {
        var transport = Return.GetMainWorldReturnTransport(WorldManager.DefaultInstanceId);

        await Assert.That(transport).IsEqualTo(Return.MainWorldReturnTransport.TeleportOnly);
    }

    [Test]
    public async Task MainWorldReturn_LoadsInstanceWhenLeavingAnInstance()
    {
        var transport = Return.GetMainWorldReturnTransport(WorldManager.DefaultInstanceId + 1);

        await Assert.That(transport).IsEqualTo(Return.MainWorldReturnTransport.LoadInstance);
    }
}
