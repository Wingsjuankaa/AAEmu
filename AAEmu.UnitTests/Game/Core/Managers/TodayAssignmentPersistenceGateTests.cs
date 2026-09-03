using System.Reflection;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class TodayAssignmentPersistenceGateTests
{
    [Test]
    public async Task MissingStorageBlocksEntryUnlockAcceptResetBulkAndCompletion()
    {
        var probes = 0;
        var manager = new TodayAssignmentManager(() => { probes++; return false; });
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "NoStorage" };
        manager.OnCharacterEnterWorld(character);
        manager.HandleRequest(character, 1, 0);
        manager.HandleRequest(character, 1, 1);
        manager.HandleRequest(character, 1, 2);
        manager.HandleReset(character, 1, 50000);
        manager.HandleAcceptAll(character, 1, [1, 2, 3]);
        manager.NotifyQuestCompleted(character, 10239);
        await Assert.That(probes).IsEqualTo(7);
        await Assert.That(LoadedDays(manager).Count).IsEqualTo(0);
    }

    [Test]
    public async Task WarmRelogCacheCannotBypassMissingStorage()
    {
        var probes = 0;
        var manager = new TodayAssignmentManager(() => { probes++; return false; });
        var character = new Character(new UnitCustomModelParams()) { Id = 42 };
        LoadedDays(manager)[character.Id] = ServerCalendar.TodayUtc;
        manager.HandleRequest(character, 1, 1);
        manager.HandleAcceptAll(character, 1, [1]);
        await Assert.That(probes).IsEqualTo(2);
    }

    [Test]
    public async Task NullCharacterDoesNotProbeStorage()
    {
        var probes = 0;
        var manager = new TodayAssignmentManager(() => { probes++; return false; });
        manager.OnCharacterEnterWorld(null);
        manager.HandleRequest(null, 1, 1);
        await Assert.That(probes).IsEqualTo(0);
    }

    private static Dictionary<uint, DateTime> LoadedDays(TodayAssignmentManager manager) =>
        (Dictionary<uint, DateTime>)typeof(TodayAssignmentManager)
            .GetField("_loadedDay", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(manager)!;
}
