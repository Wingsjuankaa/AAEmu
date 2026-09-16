using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class ClientQuestTimerPhaseTests
{
    [Test]
    public async Task RegionCreateBatchesStartPersonalTimersAndRemovalForgetsThem()
    {
        var region = new Region(null, 0, 0, 0);
        var character = new Character(null) { ObjId = 1000 };
        character.Quests = new CharacterQuests(character);
        character.Quests.SetCompletedQuestFlag(10038, true);
        // More than one native create batch. AddToCharacters deliberately bypasses
        // Doodad.AddVisibleObject, which was the missing path in the retail failure.
        for (uint id = 1; id <= 31; id++)
            region.AddObject(new Doodad
            {
                ObjId = id, Transform = null,
                Template = new DoodadTemplate { OnceOneMan = true, ClientDoodad = true }
            });

        region.AddToCharacters(character);
        var now = DateTime.UtcNow.AddSeconds(1);
        foreach (var id in new uint[] { 1, 30, 31 })
        {
            var age = character.Quests.GetClientDoodadCompletionAge(id, 10038, now);
            await Assert.That(age.HasValue).IsTrue();
            await Assert.That(Resolve(age?.TotalMilliseconds)).IsEqualTo(45397u);
        }

        var originalAge = character.Quests.GetClientDoodadCompletionAge(31, 10038, now);
        region.AddToCharacters(character); // login/cinema resend must not restart clocks
        await Assert.That(character.Quests.GetClientDoodadCompletionAge(31, 10038, now)).IsEqualTo(originalAge);
        region.RemoveFromCharacters(character);
        await Assert.That(character.Quests.GetClientDoodadCompletionAge(1, 10038, now)).IsNull();
        await Assert.That(character.Quests.GetClientDoodadCompletionAge(31, 10038, now)).IsNull();
    }

    [Test]
    public async Task IndividualVisibilityTracksOnlyPersonalClientActors()
    {
        var character = new Character(null);
        character.Quests = new CharacterQuests(character);
        character.Quests.SetCompletedQuestFlag(10038, true);
        var personal = new Doodad { ObjId = 1,
            Template = new DoodadTemplate { OnceOneMan = true, ClientDoodad = true } };
        personal.AddVisibleObject(character);
        await Assert.That(character.Quests.GetClientDoodadCompletionAge(1, 10038, DateTime.UtcNow)).IsNotNull();
        personal.RemoveVisibleObject(character);
        await Assert.That(character.Quests.GetClientDoodadCompletionAge(1, 10038, DateTime.UtcNow)).IsNull();
        foreach (var flags in new[] { (true, false), (false, true), (false, false) })
        {
            new Doodad { ObjId = 2, Template = new DoodadTemplate
                { OnceOneMan = flags.Item1, ClientDoodad = flags.Item2 } }.AddVisibleObject(character);
            await Assert.That(character.Quests.GetClientDoodadCompletionAge(2, 10038, DateTime.UtcNow)).IsNull();
        }
    }

    // Native r575 doodad15353: completed10038 ->45391 ->500ms->45397,
    // whose quest offer2198 starts10159. Its Progress edge opens Use44495.
    private static IEnumerable<DoodadFuncQuestReact> Reacts(uint phase) => phase switch
    {
        45390 => [new() { QuestId = 10038, QuestStatus = QuestStatus.Completed, NextPhase = 45391 }],
        45391 => [new() { QuestId = 10159, QuestStatus = QuestStatus.Completed, NextPhase = 45396 },
                  new() { QuestId = 10159, QuestStatus = QuestStatus.Ready, NextPhase = 45394 }],
        45397 => [new() { QuestId = 10159, QuestStatus = QuestStatus.Progress, NextPhase = 45392 }],
        _ => []
    };

    private static uint Resolve(double? elapsed, QuestStatus successor = QuestStatus.Invalid, bool completed = true)
        => Doodad.ResolveQuestReactPhase(45390, Reacts,
            id => id == 10038 && completed ? (true, QuestStatus.Completed, 0u)
                : id == 10159 && successor != QuestStatus.Invalid ? (true, successor, 0u)
                : (false, QuestStatus.Invalid, 0u),
            getTimer: phase => phase == 45391 ? new() { Delay = 500, NextPhase = 45397 } : null,
            getCompletionAge: react => react.QuestStatus == QuestStatus.Completed && elapsed.HasValue
                ? TimeSpan.FromMilliseconds(elapsed.Value) : null);

    [Test]
    [Arguments(0, 45391u)]
    [Arguments(499, 45391u)]
    [Arguments(500, 45397u)]
    [Arguments(12000, 45397u)]
    public async Task OfferAppearsOnlyAfterNativeHalfSecond(int elapsed, uint expected)
        => await Assert.That(Resolve(elapsed)).IsEqualTo(expected);

    [Test]
    public async Task MissingCompletionOrObservationCannotAdvanceTimer()
    {
        await Assert.That(Resolve(null)).IsEqualTo(45391u);
        await Assert.That(Resolve(12000, completed: false)).IsEqualTo(45390u);
    }

    [Test]
    public async Task AcceptedReadyAndCompletedSuccessorResolveTheirOwnNativePhases()
    {
        await Assert.That(Resolve(12000, QuestStatus.Progress)).IsEqualTo(45392u);
        await Assert.That(Resolve(12000, QuestStatus.Ready)).IsEqualTo(45394u);
        await Assert.That(Resolve(12000, QuestStatus.Completed)).IsEqualTo(45396u);
    }

    [Test]
    public async Task ConsecutiveTimersConsumeElapsedTimeAndCyclesTerminate()
    {
        uint Walk(int elapsed) => Doodad.ResolveQuestReactPhase(45390, Reacts,
            id => id == 10038 ? (true, QuestStatus.Completed, 0u) : (false, QuestStatus.Invalid, 0u),
            getTimer: phase => phase switch
            {
                45391 => new() { Delay = 500, NextPhase = 45397 },
                45397 => new() { Delay = 500, NextPhase = 45391 },
                _ => null
            }, getCompletionAge: _ => TimeSpan.FromMilliseconds(elapsed));
        await Assert.That(Walk(999)).IsEqualTo(45397u);
        await Assert.That(Walk(1000)).IsEqualTo(45391u);
    }

    [Test]
    public async Task VisibilityAndCompletionClocksArePerCharacterAndResetOnDespawn()
    {
        var first = new CharacterQuests(new Character(null));
        var second = new CharacterQuests(new Character(null));
        first.ObserveClientDoodadPhase(1);
        first.SetCompletedQuestFlag(10038, true);
        var afterCompletion = DateTime.UtcNow.AddMilliseconds(501);
        await Assert.That(first.GetClientDoodadCompletionAge(1, 10038, afterCompletion)!.Value.TotalMilliseconds >= 500).IsTrue();
        await Assert.That(second.GetClientDoodadCompletionAge(1, 10038, afterCompletion)).IsNull();
        first.ForgetClientDoodadPhase(1);
        await Assert.That(first.GetClientDoodadCompletionAge(1, 10038, afterCompletion)).IsNull();
        first.ObserveClientDoodadPhase(1);
        await Assert.That(first.GetClientDoodadCompletionAge(1, 10038, DateTime.MinValue)).IsEqualTo(TimeSpan.Zero);
        first.SetCompletedQuestFlag(10038, false);
        await Assert.That(first.GetClientDoodadCompletionAge(1, 10038, afterCompletion)).IsNull();
    }
}
