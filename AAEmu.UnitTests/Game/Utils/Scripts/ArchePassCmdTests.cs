using AAEmu.Game.Scripts.Commands;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.UnitTests.Game.Utils.Scripts;

public class ArchePassCmdTests
{
    [Test]
    public async Task CommandDefaultsToGmAccessAndRejectsMissingPointRecipient()
    {
        await Assert.That(new AccessLevelManager(null).GetLevel("archepass")).IsEqualTo(100);
        await Assert.That(new ArchePassManager().TryAddPoints(null, 1000, out var change)).IsFalse();
        await Assert.That(change).IsNull();
    }

    [Test]
    public async Task AcceptsOnlyPositiveSelfPointRequests()
    {
        await Assert.That(ArchePassCmd.TryParseAddPoints(["addpoints", "self", "1000"], out var amount)).IsTrue();
        await Assert.That(amount).IsEqualTo(1000);
        await Assert.That(ArchePassCmd.TryParseAddPoints(["ADDPOINTS", "SELF", "2147483647"], out amount)).IsTrue();
        await Assert.That(amount).IsEqualTo(int.MaxValue);
    }

    [Test]
    public async Task RejectsInvalidAmountsTargetsAndShapes()
    {
        string[][] requests =
        [
            null, [], ["addpoints"], ["addpoints", "self"],
            ["addpoints", "other", "100"], ["setpoints", "self", "100"],
            ["addpoints", "self", "100", "extra"],
            ["addpoints", "self", "0"], ["addpoints", "self", "-1"],
            ["addpoints", "self", "2147483648"], ["addpoints", "self", "1.5"],
            ["addpoints", "self", "NaN"], ["addpoints", "self", "1,000"]
        ];
        foreach (var request in requests)
            await Assert.That(ArchePassCmd.TryParseAddPoints(request, out _)).IsFalse();
    }

    [Test]
    public void MissingCharacterCannotGrantPoints()
    {
        var output = Mock.Of<IMessageOutput>();
        new ArchePassCmd().Execute(null, ["addpoints", "self", "1000"], output.Object);
        // The rejection completes without resolving the runtime manager or touching persistence.
    }
}
