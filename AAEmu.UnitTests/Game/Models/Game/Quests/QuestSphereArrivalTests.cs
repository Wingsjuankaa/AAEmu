using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class QuestSphereArrivalTests
{
    private static readonly FieldInfo Instance = typeof(Singleton<QuestManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previous;

    [Before(Test)]
    public void Setup()
    {
        _previous = Instance.GetValue(null);
        Instance.SetValue(null, new QuestManager(Mock.Of<ITaskManager>().Object, Mock.Of<IZoneManager>().Object));
    }

    [After(Test)]
    public void Cleanup() => Instance.SetValue(null, _previous);

    [Test]
    public async Task NemiRiver_LeavingScoutThenReachingCaptainRetainsBothArrivals()
    {
        var (quest, _) = CreateQuest();
        var scout = Arrival(quest, 39877, 62191, 2826, 0);
        var captain = Arrival(quest, 40073, 62368, 2814, 1);
        Enter(scout, 39877, 2826);
        Exit(scout, 39877, 2826);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        await Assert.That(quest.Objectives[1]).IsEqualTo(0);
        Enter(captain, 40073, 2814);
        Exit(captain, 40073, 2814);
        await Assert.That(scout.RunAct()).IsTrue();
        await Assert.That(captain.RunAct()).IsTrue();
    }

    [Test]
    public async Task UnrelatedComponentDoesNotCreditAndRepeatedArrivalDoesNotAccumulate()
    {
        var (quest, manager) = CreateQuest();
        var scout = Arrival(quest, 39877, 62191, 2826, 0);
        Enter(scout, 40073, 2814);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
        Enter(scout, 39877, 2826);
        quest.StartingEvaluation();
        Exit(scout, 39877, 2826);
        Enter(scout, 39877, 2826);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        manager.EnqueueEvaluation(quest).WasCalled(Times.Once);
    }

    [Test]
    public async Task PresenceConditionStillClearsOnExit()
    {
        var (quest, _) = CreateQuest();
        var component = Component(quest, 39877);
        var template = new QuestActCheckSphere(component.Template)
        {
            ActId = 1, SphereId = 2826, ThisComponentObjectiveIndex = 0
        };
        var act = new QuestAct(component, template);
        Enter(act, 39877, 2826);
        await Assert.That(quest.Objectives[0]).IsEqualTo(1);
        Exit(act, 39877, 2826);
        await Assert.That(quest.Objectives[0]).IsEqualTo(0);
    }

    private static void Enter(QuestAct act, uint component, uint sphere) => act.OnEnterSphere(null,
        new OnEnterSphereArgs { SphereQuest = new SphereQuest { QuestId = 9180, ComponentId = component, SphereId = sphere } });
    private static void Exit(QuestAct act, uint component, uint sphere) => act.OnExitSphere(null,
        new OnExitSphereArgs { SphereQuest = new SphereQuest { QuestId = 9180, ComponentId = component, SphereId = sphere } });

    private static QuestComponent Component(Quest quest, uint id) =>
        new(new QuestStep(QuestComponentKind.Progress, quest),
            new QuestComponentTemplate((QuestTemplate)quest.Template) { Id = id, KindId = QuestComponentKind.Progress });

    private static QuestAct Arrival(Quest quest, uint componentId, uint actId, uint sphere, byte index)
    {
        var component = Component(quest, componentId);
        return new QuestAct(component, new QuestActObjSphere(component.Template)
        {
            ActId = actId, SphereId = sphere, ThisComponentObjectiveIndex = index
        });
    }

    private static (Quest, Mock<IQuestManager>) CreateQuest()
    {
        var manager = Mock.Of<IQuestManager>();
        var quest = new Quest(new QuestTemplate { Id = 9180 }, Mock.Of<ICharacter>().Object,
            manager.Object, Mock.Of<ITaskManager>().Object, Mock.Of<ISkillManager>().Object,
            Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        quest.QuestInitialized();
        return (quest, manager);
    }
}
