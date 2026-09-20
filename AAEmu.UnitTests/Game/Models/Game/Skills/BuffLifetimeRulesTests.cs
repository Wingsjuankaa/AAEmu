using System.Reflection;

using AAEmu.Commons.Network;
using AAEmu.Game;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

/// <summary>
/// <c>buffs.max_life_time</c> (E9f): the ceiling on how long one instance may live, applied where the
/// instance's duration is decided and again where it is written.
/// </summary>
/// <remarks>
/// The second half is the one with teeth. <c>AddBuff</c> and <c>Buff.OverwriteWith</c> both write
/// <c>Duration</c> directly and <c>OverwriteWith</c> follows the stack rule rather than the base
/// duration, so a refresh of an Extend family would put the buff back past its ceiling unless the write
/// goes through the same clamp. What is asserted here is that both paths land on the ceiling.
/// </remarks>
[NotInParallel]
public class BuffLifetimeRulesTests
{
    private sealed class RecordingUnit : Unit
    {
        public readonly List<(Type Type, byte[] Body)> Sent = [];
        public override void BroadcastPacket(GamePacket packet, bool self) =>
            Sent.Add((packet.GetType(), packet.Write(new PacketStream()).GetBytes()));
    }

    private const uint CappedBuffId = 94001;

    private SingletonScope<BuffGameData> _buffGameData;
    private SingletonScope<SkillManager> _skills;
    private SingletonScope<TaskManager> _tasks;
    private SingletonScope<EffectTaskManager> _effectTasks;

    [Before(Test)]
    public void InstallContentLookups()
    {
        var gameData = new BuffGameData();
        SetField(gameData, "_buffModifiers", new Dictionary<uint, List<BuffModifier>>());
        SetField(gameData, "_buffTolerances", new Dictionary<uint, BuffTolerance>());
        SetField(gameData, "_buffTolerancesById", new Dictionary<uint, BuffTolerance>());
        _buffGameData = new SingletonScope<BuffGameData>(gameData);

        var skillManager = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        SetField(skillManager, "_buffs", new Dictionary<uint, BuffTemplate>
        {
            [CappedBuffId] = new BuffTemplate { Id = CappedBuffId, Duration = 8000, MaxLifeTime = 4000u }
        });
        SetField(skillManager, "_buffTags", new Dictionary<uint, List<uint>>());
        SetField(skillManager, "_taggedBuffs", new Dictionary<uint, List<uint>>());
        _skills = new SingletonScope<SkillManager>(skillManager);

        // A timed instance is scheduled through these two, so the clamp has to be observed on a path that
        // actually reaches AddDispelTask.
        var taskManager = new TaskManager(Mock.Of<ITickManager>().Object);
        _tasks = new SingletonScope<TaskManager>(taskManager);
        _effectTasks = new SingletonScope<EffectTaskManager>(new EffectTaskManager(taskManager));
    }

    [After(Test)]
    public void RestoreContentLookups()
    {
        _effectTasks.Dispose();
        _tasks.Dispose();
        _skills.Dispose();
        _buffGameData.Dispose();
    }

    private static void SetField(object target, string name, object value)
        => target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);

    [Test]
    public async Task ClampedDuration_ShortensADurationPastTheCeiling()
    {
        // 31544 전율하는 매: 파도: duration 8,000, max_life_time 4,000.
        await Assert.That(BuffLifetimeRules.ClampedDuration(8000, 4000)).IsEqualTo(4000);
    }

    [Test]
    public async Task ClampedDuration_LeavesADurationUnderTheCeilingAlone()
    {
        // The ceiling is a ceiling: 18379 방패 진격 is 1,000 under 1,000, 2287 강력한 화염 7,000 under
        // 7,000, and 32795 전율하는 매: 생명 4,000 under 8,000. None of them may be lengthened to it.
        await Assert.That(BuffLifetimeRules.ClampedDuration(1000, 20000)).IsEqualTo(1000);
        await Assert.That(BuffLifetimeRules.ClampedDuration(2000, 2000)).IsEqualTo(2000);
        await Assert.That(BuffLifetimeRules.ClampedDuration(4000, 8000)).IsEqualTo(4000);
    }

    [Test]
    public async Task ClampedDuration_GivesADurationZeroFamilyItsAuthoredExpiry()
    {
        // 23749 깃발의 기운 carries duration 0 and max_life_time 11,000, 23151 추격: 파도 0 against 5,000.
        // Duration 0 is this server's permanent, so these 30 rows are the ones the clamp actually changes
        // from unbounded to bounded.
        await Assert.That(BuffLifetimeRules.ClampedDuration(0, 11000)).IsEqualTo(11000);
        await Assert.That(BuffLifetimeRules.ClampedDuration(0, 5000)).IsEqualTo(5000);
    }

    [Test]
    public async Task ClampedDuration_NoCeilingIsExactlyTheOldPath()
    {
        // 30,558 of the 30,654 shipped buffs leave the column at zero. Every one of them has to come back
        // with the duration it had, including the 0 that means permanent - the clamp must not invent an
        // expiry for a family whose content says there is none.
        await Assert.That(BuffLifetimeRules.ClampedDuration(0, 0)).IsEqualTo(0);
        await Assert.That(BuffLifetimeRules.ClampedDuration(8000, 0)).IsEqualTo(8000);
        await Assert.That(BuffLifetimeRules.ClampedDuration(-1, 0)).IsEqualTo(-1);
    }

    [Test]
    public async Task AddBuff_HoldsTheInstanceAtItsCeiling()
    {
        var owner = new Unit { ObjId = 1 };
        var caster = new Unit { ObjId = 2 };
        var template = SkillManager.Instance.GetBuffTemplate(CappedBuffId);
        var buff = new Buff(owner, caster, new SkillCasterUnit(caster.ObjId), template, null, DateTime.UtcNow)
        {
            AbLevel = 1
        };

        owner.Buffs.AddBuff(buff);

        await Assert.That(buff.Duration).IsEqualTo(4000);
        await Assert.That(buff.GetTimeLeft()).IsLessThanOrEqualTo(4000);
    }

    [Test]
    public async Task Refresh_HoldsTheInstanceAtItsCeilingToo()
    {
        // The stack rule decides what a second application does to the timer, and neither branch may take
        // the instance back past the ceiling: Refresh replaces the duration, Extend adds to what is left.
        var owner = new Unit { ObjId = 1 };
        var caster = new Unit { ObjId = 2 };
        var template = SkillManager.Instance.GetBuffTemplate(CappedBuffId);

        Buff Apply() => new(owner, caster, new SkillCasterUnit(caster.ObjId), template, null, DateTime.UtcNow)
        {
            AbLevel = 1
        };

        owner.Buffs.AddBuff(Apply());
        owner.Buffs.AddBuff(Apply());

        var live = owner.Buffs.GetEffectByTemplate(template);

        await Assert.That(live).IsNotNull();
        await Assert.That(live!.Duration).IsLessThanOrEqualTo(4000);
    }

    [Test]
    [Arguments(182u)]
    [Arguments(22689u)]
    [Arguments(22690u)]
    public async Task Frenzy_ExtensionsKeepNativeClientAndZoneTimersBounded_AndExpireOnce(uint buffId)
    {
        // r575 buffs + SCBuffCreated consumer 0xbd5260: Extend adds the application
        // to total lifetime, retains elapsed, and caps remaining (not total) at 40 s.
        var template = new BuffTemplate
        {
            Id = buffId, Duration = 20000, MaxLifeTime = 40000, MaxStack = 1,
            StackRule = BuffStackRule.Extend, Kind = BuffKind.Good
        };
        ((Dictionary<uint, BuffTemplate>)typeof(SkillManager).GetField("_buffs", BindingFlags.Instance | BindingFlags.NonPublic)!
            .GetValue(SkillManager.Instance)!)[buffId] = template;
        var owner = new RecordingUnit { ObjId = 1539 };
        Buff Application() => new(owner, owner, new SkillCasterUnit(owner.ObjId), template, null, DateTime.UtcNow);
        var previousAuthority = WorldIntegration.ZoneAuthority;
        var previousCreate = WorldIntegration.RelayBuffCreatedToZone;
        var previousRemove = WorldIntegration.RelayBuffRemovedToZone;
        var previousUpdate = WorldIntegration.RelayBuffUpdatedToZone;
        var zoneEvents = new List<string>();
        var zoneCreates = new List<byte[]>();
        try
        {
            WorldIntegration.ZoneAuthority = true;
            WorldIntegration.RelayBuffCreatedToZone = (_, body) => { zoneEvents.Add("create"); zoneCreates.Add(body); };
            WorldIntegration.RelayBuffRemovedToZone = (_, _) => zoneEvents.Add("remove");
            WorldIntegration.RelayBuffUpdatedToZone = (_, _, _, _, _, _) => zoneEvents.Add("update");
            owner.Buffs.AddBuff(Application());
            var live = owner.Buffs.GetEffectByTemplate(template);
            var index = live.Index;
            var staleDeadline = new DispelTask(live);
            live.StartTime = DateTime.UtcNow.AddSeconds(-3);
            var origin = live.StartTime;
            var clientLifetime = 20000u;
            const uint clientElapsed = 3000;
            for (var application = 0; application < 10; application++)
            {
                owner.Sent.Clear();
                zoneEvents.Clear();
                owner.Buffs.AddBuff(Application());
                await Assert.That(live.StartTime).IsEqualTo(origin);
                await Assert.That(live.Index).IsEqualTo(index);
                await Assert.That(owner.Buffs.GetBuffCountById(buffId)).IsEqualTo(1);
                await Assert.That(live.GetTimeLeft()).IsLessThanOrEqualTo(40000);
                await Assert.That(owner.Sent.Count).IsEqualTo(1);
                await Assert.That(owner.Sent[0].Type).IsEqualTo(typeof(SCBuffCreatedPacket));
                var incomingDuration = DurationFromCreate(owner.Sent[0].Body);
                await Assert.That(incomingDuration).IsEqualTo(20000u);
                clientLifetime = Math.Min(clientLifetime + incomingDuration, clientElapsed + 40000);
                await Assert.That(Math.Abs((clientLifetime - clientElapsed) - live.GetTimeLeft())).IsLessThan(500);
                await Assert.That(string.Join(",", zoneEvents)).IsEqualTo("remove,create");
                await Assert.That(Math.Abs(DurationFromCreate(zoneCreates[^1]) - live.GetTimeLeft())).IsLessThan(100);
                staleDeadline.Execute();
                await Assert.That(live.IsEnded()).IsFalse();
            }
            owner.Sent.Clear();
            zoneEvents.Clear();
            live.StartTime = DateTime.UtcNow.AddMilliseconds(-live.Duration - 1);
            staleDeadline.Execute();
            staleDeadline.Execute();
            await Assert.That(owner.Buffs.GetBuffCountById(buffId)).IsEqualTo(0);
            await Assert.That(live.IsEnded()).IsTrue();
            await Assert.That(owner.Sent.Count(p => p.Type == typeof(SCBuffRemovedPacket))).IsEqualTo(1);
            await Assert.That(string.Join(",", zoneEvents)).IsEqualTo("remove");
        }
        finally
        {
            WorldIntegration.ZoneAuthority = previousAuthority;
            WorldIntegration.RelayBuffCreatedToZone = previousCreate;
            WorldIntegration.RelayBuffRemovedToZone = previousRemove;
            WorldIntegration.RelayBuffUpdatedToZone = previousUpdate;
        }
    }

    private static uint DurationFromCreate(byte[] body)
    {
        var stream = new PacketStream(body) { Pos = 34 }; // unit caster, cast id, target, index, BuffData header
        return stream.ReadPisc(4)[1] * 10;
    }
}
