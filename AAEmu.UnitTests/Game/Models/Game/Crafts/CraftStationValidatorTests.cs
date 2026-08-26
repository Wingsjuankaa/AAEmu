using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.DoodadObj.Static;

namespace AAEmu.UnitTests.Game.Models.Game.Crafts;

public class CraftStationValidatorTests
{
    [Test]
    public async Task RequiredStationMustExistAndMatchExactly()
    {
        var craft = new Craft { ReqDoodadId = 42 };

        var missing = CraftStationValidator.TryValidate(
            craft, false, 0, null, out var missingFailure);
        var wrong = CraftStationValidator.TryValidate(
            craft, true, 41, DoodadFuncPermission.Public, out var wrongFailure);
        var correct = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Public, out var correctFailure);

        await Assert.That(missing).IsFalse();
        await Assert.That(missingFailure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
        await Assert.That(wrong).IsFalse();
        await Assert.That(wrongFailure.Code).IsEqualTo(CraftFailureCode.StationUnavailable);
        await Assert.That(correct).IsTrue();
        await Assert.That(correctFailure).IsEqualTo(CraftFailure.None);
    }

    [Test]
    public async Task UnprovenPermissionModesFailClosed()
    {
        var craft = new Craft { ReqDoodadId = 42 };

        var accepted = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Public, out _);
        var rejected = CraftStationValidator.TryValidate(
            craft, true, 42, DoodadFuncPermission.Owner, out var failure);

        await Assert.That(accepted).IsTrue();
        await Assert.That(rejected).IsFalse();
        await Assert.That(failure.Code).IsEqualTo(CraftFailureCode.PermissionDenied);
    }
}
