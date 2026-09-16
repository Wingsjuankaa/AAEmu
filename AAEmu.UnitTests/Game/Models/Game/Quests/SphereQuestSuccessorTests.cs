using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Spheres;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class SphereQuestSuccessorTests
{
    private readonly List<(FieldInfo Field, object Value)> _saved = [];
    private CharacterQuests _quests;
    private Character _owner;
    private readonly SphereQuest _area = new() { SphereId = 2997, ZoneId = 378 };
    private readonly Spheres _sphere = new()
    {
        Id = 2997, SphereDetailId = 1733, SphereDetailType = "SphereQuest", EnterOrLeave = true,
        TriggerConditionId = AreaSphereTriggerCondition.TriggerEveryNTimeAfter
    };
    private readonly SphereQuests _detail = new() { Id = 1733, QuestId = 10049, QuestTriggerId = QuestTrigger.AcceptForce };
    private readonly UnitReqs _requirement = new()
    {
        Id = 69490, OwnerId = 43679, OwnerType = "QuestComponent",
        KindType = UnitReqsKindType.CompleteQuestContext, Value1 = 10048
    };

    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
        _saved.Add((field, field.GetValue(null)));
        field.SetValue(null, value);
    }

    [Before(Test)]
    public void Setup()
    {
        _owner = new Character(null);
        _owner.Quests = _quests = new CharacterQuests(_owner);
        var data = new SphereGameData();
        Set(data, "_spheres", new Dictionary<uint, Spheres> { [2997] = _sphere });
        Set(data, "_sphereQuests", new Dictionary<uint, SphereQuests> { [1733] = _detail });
        Swap(data);
        var reqs = new UnitRequirementsGameData();
        typeof(UnitRequirementsGameData).GetProperty("_unitReqsByOwnerType", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(reqs, new Dictionary<string, List<UnitReqs>> { ["QuestComponent"] = [_requirement] });
        Swap(reqs);
        var manager = new QuestManager(Mock.Of<ITaskManager>().Object, Mock.Of<IZoneManager>().Object);
        var template = new QuestTemplate { Id = 10049 };
        template.Components[43679] = new QuestComponentTemplate(template) { Id = 43679, KindId = QuestComponentKind.Start };
        ((Dictionary<uint, QuestTemplate>)typeof(QuestManager).GetField("_questTemplates", BindingFlags.NonPublic | BindingFlags.Instance)!
            .GetValue(manager)!)[10049] = template;
        Swap(manager);
        Set(_quests, "_insideQuestAreaSphereIds", new HashSet<uint> { 2997 });
    }

    [After(Test)]
    public void Cleanup()
    {
        foreach (var (field, value) in _saved) field.SetValue(null, value);
    }

    [Test]
    public async Task GuardianCompletionRetriesAcceptanceWithoutAnotherAreaEntry()
    {
        // Actual r575 prerequisite rejects the original entry, without changing quests.
        await Assert.That(_quests.AddQuestFromSphere(10049, 2997)).IsFalse();
        await Assert.That(_quests.ActiveQuests.Count).IsEqualTo(0);
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);

        _quests.SetCompletedQuestFlag(10048, true);
        var starts = _quests.GetPendingSphereQuestStarts([_area]);
        await Assert.That(starts.Single()).IsEqualTo((10049u, 2997u));
        await Assert.That(_requirement.Validate(_owner, _owner).ResultKey)
            .IsEqualTo(AAEmu.Game.Models.Game.Skills.Static.SkillResultKeys.ok);
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);
        _quests.SetCompletedQuestFlag(10048, true); // Duplicate completion notification.
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);
    }

    [Test]
    public async Task UnrelatedCompletionDoesNotBypassTheSuccessorRequirement()
    {
        _quests.SetCompletedQuestFlag(10047, true);
        foreach (var (quest, sphere) in _quests.GetPendingSphereQuestStarts([_area]))
            await Assert.That(_quests.AddQuestFromSphere(quest, sphere)).IsFalse();
        await Assert.That(_quests.ActiveQuests.Count).IsEqualTo(0);
    }

    [Test]
    public async Task LeavingTheAreaAndCompletedOrActiveSuccessorsCannotStartAgain()
    {
        _quests.SetCompletedQuestFlag(10048, true);
        await Assert.That(_quests.GetPendingSphereQuestStarts([]).Count).IsEqualTo(0);
        _quests.SetCompletedQuestFlag(10049, true);
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);
        _quests.SetCompletedQuestFlag(10049, false);
        _quests.ActiveQuests[10049] = null; // Presence alone must exclude an active successor.
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);
    }

    [Test]
    [Arguments(1, 0u, true, "SphereQuest", 3)]
    [Arguments(2, 0u, true, "SphereQuest", 3)]
    [Arguments(3, 1000u, true, "SphereQuest", 3)]
    [Arguments(3, 0u, false, "SphereQuest", 3)]
    [Arguments(3, 0u, true, "SphereBuff", 3)]
    [Arguments(3, 0u, true, "SphereQuest", 1)]
    public async Task NonAcceptanceAndNonImmediateAreasAreNotReplayed(int condition, uint time, bool enter, string kind, int trigger)
    {
        _sphere.TriggerConditionId = (AreaSphereTriggerCondition)condition;
        _sphere.TriggerConditionTime = time;
        _sphere.EnterOrLeave = enter;
        _sphere.SphereDetailType = kind;
        _detail.QuestTriggerId = (QuestTrigger)trigger;
        _quests.SetCompletedQuestFlag(10048, true);
        await Assert.That(_quests.GetPendingSphereQuestStarts([_area]).Count).IsEqualTo(0);
    }

    private static void Set(object target, string name, object value) => target.GetType()
        .GetField(name, BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(target, value);
}
