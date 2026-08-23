using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.Quests.Static;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class DoodadQuestReactPhaseTests
{
    private static readonly Dictionary<uint, DoodadFuncQuestReact[]> AlcantoPhases = new()
    {
        [41880] =
        [
            new() { QuestId = 6710, QuestStatus = QuestStatus.Completed, NextPhase = 41974 },
            new() { QuestId = 6709, QuestStatus = QuestStatus.Progress, NextPhase = 41881 },
            new() { QuestId = 6709, QuestStatus = QuestStatus.Ready, NextPhase = 41973 },
            new() { QuestId = 6709, QuestStatus = QuestStatus.Completed, NextPhase = 41973 }
        ],
        [41881] =
        [
            new() { QuestId = 6709, QuestStatus = QuestStatus.Dropped, NextPhase = 41880 }
        ],
        [41973] =
        [
            new() { QuestId = 6709, QuestStatus = QuestStatus.Dropped, NextPhase = 41880 }
        ]
    };

    [Test]
    [Arguments(QuestStatus.Progress, 41881u)]
    [Arguments(QuestStatus.Ready, 41973u)]
    [Arguments(QuestStatus.Completed, 41973u)]
    public async Task Alcanto6709_ResolvesNativeCharacterPhase(QuestStatus status, uint expectedPhase)
    {
        var phase = Resolve(6709, status);

        await Assert.That(phase).IsEqualTo(expectedPhase);
    }

    [Test]
    public async Task SuccessorCompletion_TakesEarlierNativeEdge()
    {
        var phase = Doodad.ResolveQuestReactPhase(
            41880,
            GetReacts,
            questId => questId switch
            {
                6709 => (true, QuestStatus.Completed, 0u),
                6710 => (true, QuestStatus.Completed, 0u),
                _ => (false, QuestStatus.Invalid, 0u)
            });

        await Assert.That(phase).IsEqualTo(41974u);
    }

    [Test]
    public async Task ComponentSpecificEdge_RequiresCurrentComponent()
    {
        var reacts = new Dictionary<uint, DoodadFuncQuestReact[]>
        {
            [10] = [new() { QuestId = 9173, QuestStatus = QuestStatus.Progress, QuestComponentId = 39849, NextPhase = 11 }]
        };

        var wrongComponent = Doodad.ResolveQuestReactPhase(
            10,
            phase => reacts.GetValueOrDefault(phase) ?? [],
            _ => (true, QuestStatus.Progress, 39998u));
        var matchingComponent = Doodad.ResolveQuestReactPhase(
            10,
            phase => reacts.GetValueOrDefault(phase) ?? [],
            _ => (true, QuestStatus.Progress, 39849u));

        await Assert.That(wrongComponent).IsEqualTo(10u);
        await Assert.That(matchingComponent).IsEqualTo(11u);
    }

    private static uint Resolve(uint questId, QuestStatus status)
        => Doodad.ResolveQuestReactPhase(
            41880,
            GetReacts,
            id => id == questId
                ? (true, status, 0u)
                : (false, QuestStatus.Invalid, 0u));

    private static IEnumerable<DoodadFuncQuestReact> GetReacts(uint phase)
        => AlcantoPhases.GetValueOrDefault(phase) ?? [];
}
