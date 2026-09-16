using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Spheres;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class AnthalonSphereSkillTests
{
    private readonly List<(FieldInfo Field, object Value)> _saved = [];
    private readonly List<WorldNpcSpawnerEventRequest> _requests = [];
    private Character _owner;
    private CharacterQuests _quests;
    private Quest _quest;
    private bool _oldAuthority;
    private Func<uint, bool> _oldProbe;
    private Func<WorldNpcSpawnerEventRequest, bool> _oldRelay;
    private readonly SphereQuest _geo = new() { SphereId = 3044, ZoneId = 384 };
    private readonly Spheres _sphere = new()
    {
        Id = 3044, SphereDetailType = "SphereSkill", SphereDetailId = 312, EnterOrLeave = true,
        TriggerConditionId = AreaSphereTriggerCondition.TriggerEveryNTimeAfter, TriggerConditionTime = 3600000
    };

    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
        _saved.Add((field, field.GetValue(null)));
        field.SetValue(null, value);
    }

    private static void Set(object target, string field, object value) => target.GetType()
        .GetField(field, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);

    [Before(Test)]
    public void Setup()
    {
        _owner = new Character(null) { Id = 1007, ObjId = 1046 };
        _owner.Quests = _quests = new CharacterQuests(_owner);
        _quest = new Quest(null, _owner, null, null, null, null, null);
        Set(_quest, "_step", QuestComponentKind.Progress);
        _quests.ActiveQuests[10101] = _quest;
        var data = new SphereGameData();
        Set(data, "_sphereSkills", new Dictionary<uint, SphereSkills>
        {
            [312] = new() { Id = 312, SkillId = 44277, MinRate = 100, MaxRate = 100 }
        });
        Swap(data);
        var reqs = new UnitRequirementsGameData();
        typeof(UnitRequirementsGameData).GetProperty("_unitReqsByOwnerType", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(reqs, new Dictionary<string, List<UnitReqs>>
            {
                ["Sphere"] = [new() { Id = 69953, OwnerId = 3044, OwnerType = "Sphere",
                    KindType = UnitReqsKindType.ProgressQuestContext, Value1 = 10101 }]
            });
        Swap(reqs);
        _oldAuthority = WorldIntegration.ZoneAuthority;
        _oldProbe = WorldIntegration.IsZoneLoaded;
        _oldRelay = WorldIntegration.RelayNpcSpawnerEventToZone;
        WorldIntegration.ZoneAuthority = true;
        WorldIntegration.IsZoneLoaded = zone => zone == 384;
        WorldIntegration.RelayNpcSpawnerEventToZone = request => { _requests.Add(request); return true; };
    }

    [After(Test)]
    public void Cleanup()
    {
        WorldIntegration.ZoneAuthority = _oldAuthority;
        WorldIntegration.IsZoneLoaded = _oldProbe;
        WorldIntegration.RelayNpcSpawnerEventToZone = _oldRelay;
        foreach (var (field, value) in _saved) field.SetValue(null, value);
    }

    private bool Spawn(uint skill)
    {
        if (skill != 44277) throw new InvalidOperationException("Wrong native skill");
        new NpcSpawnerSpawnEffect { SpawnerId = 205923, ActivationState = false }
            .Apply(_owner, null, _owner, null, null, null, null, DateTime.UtcNow);
        return true;
    }

    [Test]
    public async Task EnterSpawnsNativeEncounterOnceAndRespectsOneHourInterval()
    {
        var now = DateTime.UtcNow;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsTrue();
        await Assert.That(_requests.Single().SpawnerId).IsEqualTo(205923u);
        await Assert.That(_requests.Single().CreatorObjId).IsEqualTo(1046u);
        await Assert.That(_requests.Single().Event).IsEqualTo(NpcSpawnerEvent.SpawnAllOnceAndDeactivate);
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now.AddMinutes(59), Spawn)).IsFalse();
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now.AddHours(1), Spawn)).IsTrue();
        await Assert.That(_requests.Count).IsEqualTo(2);
        await Assert.That(_quest.Step).IsEqualTo(QuestComponentKind.Progress); // Spawn isn't quest completion.
    }

    [Test]
    public async Task MissingQuestReadyQuestAndUnavailableHostNeverSpawnOrConsumeInterval()
    {
        var now = DateTime.UtcNow;
        _quests.ActiveQuests.Clear();
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsFalse();
        _quests.ActiveQuests[10101] = _quest;
        Set(_quest, "_step", QuestComponentKind.Ready);
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsFalse();
        Set(_quest, "_step", QuestComponentKind.Progress);
        WorldIntegration.IsZoneLoaded = _ => false;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsFalse();
        WorldIntegration.IsZoneLoaded = null;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsFalse();
        await Assert.That(_requests.Count).IsEqualTo(0);
        WorldIntegration.IsZoneLoaded = _ => true;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsTrue();
    }

    [Test]
    public async Task FailedSkillAndOtherAreasDoNotConsumeInterval()
    {
        var now = DateTime.UtcNow;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, _ => false)).IsFalse();
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(new() { SphereId = 3044, ZoneId = 382 }, _sphere, now, Spawn)).IsFalse();
        _sphere.EnterOrLeave = false;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsFalse();
        _sphere.EnterOrLeave = true;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsTrue();
    }

    [Test]
    public async Task CooldownDoesNotLeakToAnotherPlayerOrInstance()
    {
        var now = DateTime.UtcNow;
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsTrue();
        Set(_owner.Transform, "_instanceId", 101u);
        await Assert.That(_quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, Spawn)).IsTrue();
        var other = new Character(null) { Id = 1008 };
        other.Quests = new CharacterQuests(other);
        other.Quests.ActiveQuests[10101] = _quest;
        await Assert.That(other.Quests.TryTriggerQuestAreaSphereSkill(_geo, _sphere, now, _ => true)).IsTrue();
    }
}
