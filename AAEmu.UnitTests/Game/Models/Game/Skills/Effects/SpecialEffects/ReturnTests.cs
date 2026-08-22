using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;

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
    public async Task ReturnImplementation_DoesNotDeclareLegacyInstanceOne()
    {
        var sourcePath = Path.Combine(
            FindRepositoryRoot(),
            "AAEmu.Game",
            "Models",
            "Game",
            "Skills",
            "Effects",
            "SpecialEffects",
            "Return.cs");
        var source = await File.ReadAllTextAsync(sourcePath);

        await Assert.That(source).Contains("var mainWorldInstanceId = WorldManager.DefaultInstanceId;");
        await Assert.That(source).Contains("new SCLoadInstancePacket(\n                    mainWorldInstanceId,");
        await Assert.That(source).DoesNotContain("new SCLoadInstancePacket(\n                    1,");
    }

    private static string FindRepositoryRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null && !File.Exists(Path.Combine(directory.FullName, "AAEmu.slnx")))
            directory = directory.Parent;

        return directory?.FullName
            ?? throw new DirectoryNotFoundException("Could not locate the AAEmu repository root.");
    }
}
