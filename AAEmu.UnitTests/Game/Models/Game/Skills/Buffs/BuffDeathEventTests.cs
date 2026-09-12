using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.Skills.Buffs;

[NotInParallel]
public class BuffDeathEventTests
{
    private sealed class CaptureEffect : EffectTemplate
    {
        public readonly List<(BaseUnit Source, BaseUnit Target)> Calls = [];
        public override bool OnActionTime => false;
        public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source, SkillObject skillObject,
            DateTime time, CompressedGamePackets packetBuilder = null) => Calls.Add((caster, target));
    }

    private readonly List<(FieldInfo Field, object Old)> _saved = [];
    private SkillManager _skills;

    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
        _saved.Add((field, field.GetValue(null)!)); field.SetValue(null, value);
    }

    [Before(Test)]
    public void Setup()
    {
        _skills = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        Swap(_skills);
        var requirements = new UnitRequirementsGameData(); Swap(requirements);
        using var db = new SqliteConnection("Data Source=:memory:"); db.Open();
        using var cmd = db.CreateCommand();
        cmd.CommandText = """
            CREATE TABLE unit_reqs(id,owner_id,owner_type,kind_id,value1,value2,enable,value3,display_msg);
            INSERT INTO unit_reqs VALUES(69765,13463,'BuffTrigger',32,10056,0,'t',0,'t');
            """;
        cmd.ExecuteNonQuery(); requirements.Load(db);
    }

    [After(Test)]
    public void Cleanup()
    {
        foreach (var (field, old) in _saved) field.SetValue(null, old);
        _saved.Clear();
    }

    private Buff Subscribe(Unit owner, Unit originalCaster, BuffTriggerTemplate trigger, uint buffId)
    {
        typeof(SkillManager).GetField("_buffTriggers", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(_skills, new Dictionary<uint, List<BuffTriggerTemplate>> { [buffId] = [trigger] });
        var buff = new Buff(owner, originalCaster, new SkillCasterUnit(originalCaster.ObjId),
            new BuffTemplate { Id = buffId }, null, DateTime.UtcNow);
        buff.Triggers.SubscribeEvents();
        return buff;
    }

    [Test]
    public async Task NativeNpcDeathTrigger_UsesKillerAsSource_AndDeadOwnerAsTarget()
    {
        var npc = new Unit(); var originalCaster = new Unit(); var killer = new Unit();
        var effect = new CaptureEffect();
        // npc19979 -> initial buff26574 -> trigger13590 -> SkillUse44464 / plot4909.
        var buff = Subscribe(npc, originalCaster, new BuffTriggerTemplate
        {
            Id = 13590, Kind = BuffEventTriggerKind.Death, SourceAgentId = 1, TargetAgentId = 0, Effect = effect
        }, 26574);
        var death = new OnDeathArgs { Killer = killer, Victim = npc };
        originalCaster.Events.OnDeath(originalCaster, death);
        await Assert.That(effect.Calls.Count).IsEqualTo(0);
        npc.Events.OnDeath(npc, death);
        await Assert.That(effect.Calls.Count).IsEqualTo(1);
        await Assert.That(effect.Calls[0].Source).IsSameReferenceAs(killer);
        await Assert.That(effect.Calls[0].Target).IsSameReferenceAs(npc);
        buff.Triggers.UnsubscribeEvents();
        npc.Events.OnDeath(npc, death);
        await Assert.That(effect.Calls.Count).IsEqualTo(1);
    }

    [Test]
    public async Task KillAny_RequiresRealVictimAndActiveQuest_AndUnsubscribes()
    {
        var player = new Character(null); player.Quests = new CharacterQuests(player);
        var victim = new Unit(); var effect = new CaptureEffect();
        var buff = Subscribe(player, player, new BuffTriggerTemplate
        {
            Id = 13463, Kind = BuffEventTriggerKind.KillAny, SourceAgentId = 0, TargetAgentId = 2, Effect = effect
        }, 25655);
        var kill = new OnKillArgs { Killer = player, Victim = victim };
        player.Events.OnKill(player, kill);
        await Assert.That(effect.Calls.Count).IsEqualTo(0);
        var quest = new Quest(null, player, null, null, null, null, null);
        typeof(Quest).GetField("_step", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(quest, QuestComponentKind.Progress);
        player.Quests.ActiveQuests.Add(10056, quest);
        player.Events.OnKill(player, new OnKillArgs { Target = player });
        player.Events.OnKill(player, kill);
        await Assert.That(effect.Calls.Count).IsEqualTo(1);
        await Assert.That(effect.Calls[0].Source).IsSameReferenceAs(player);
        await Assert.That(effect.Calls[0].Target).IsSameReferenceAs(victim);
        buff.Triggers.UnsubscribeEvents();
        player.Events.OnKill(player, kill);
        await Assert.That(effect.Calls.Count).IsEqualTo(1);
    }
}
