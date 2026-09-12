using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Scripts.Commands;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class GardenRateTests
{
    [Before(Test)]
    public void Setup() => GardenScoreRate.TrySet(1);
    [After(Test)]
    public void Cleanup() => GardenScoreRate.TrySet(1);

    [Test]
    public async Task CommandChangesRateImmediately_QueriesAndRestoresNormalRate()
    {
        var command = new GardenRate(); var player = new Character(null);
        var output = Mock.Of<IMessageOutput>().Object;
        await Assert.That(new AccessLevelManager(null).GetLevel("gardenrate")).IsEqualTo(100);
        command.Execute(player, ["20"], output);
        await Assert.That(GardenScoreRate.ScaleGain(5)).IsEqualTo(100);
        await Assert.That(GardenScoreRate.ScaleGain(160)).IsEqualTo(3200);
        command.Execute(player, [], output);
        await Assert.That(GardenScoreRate.Multiplier).IsEqualTo(20);
        command.Execute(player, ["1"], output);
        await Assert.That(GardenScoreRate.ScaleGain(160)).IsEqualTo(160);
    }

    [Test]
    public async Task InvalidCommandsLeaveRateUnchanged_AndLossesAreNotMultiplied()
    {
        var command = new GardenRate(); var player = new Character(null);
        var output = Mock.Of<IMessageOutput>().Object;
        GardenScoreRate.TrySet(10);
        foreach (var args in new[] { new[] { "0" }, ["-1"], ["1001"], ["NaN"], ["1.5"], ["2147483648"], ["20", "extra"] })
        {
            command.Execute(player, args, output);
            await Assert.That(GardenScoreRate.Multiplier).IsEqualTo(10);
        }
        await Assert.That(GardenScoreRate.ScaleGain(-2500)).IsEqualTo(-2500);
        await Assert.That(GardenScoreRate.ScaleGain(0)).IsEqualTo(0);
        GardenScoreRate.TrySet(1000);
        await Assert.That(GardenScoreRate.ScaleGain(int.MaxValue)).IsEqualTo(int.MaxValue);
    }
}
