using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Zones;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class BuffTickRequirementsTests
{
    private static readonly uint[] RankIds = [26196, 25656, 25658, 25659, 25660, 25661, 25662, 25663, 25664, 25665, 25666, 25667, 25668];
    private static readonly int[] RankScores = [0, 2500, 5400, 8600, 12600, 16900, 21600, 27000, 33100, 40000, 47500, 55800, 64800];
    private sealed class QuietCharacter() : Character(null)
    {
        public override void BroadcastPacket(GamePacket packet, bool self) { }
        public override int MaxHp => 100;
    }

    private sealed class Services : IDisposable
    {
        private readonly List<(FieldInfo Field, object Value)> _saved = [];
        public readonly SkillManager Skills = new(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        public readonly UnitRequirementsGameData Requirements = new();
        public readonly BuffTemplate Environment = new() { Id = 26390, Tick = 1000 };
        public readonly BuffTemplate Patrol = new() { Id = 25655, RequireBuffId = 26390, Tick = 10000 };
        public readonly BuffTemplate Rank = new() { Id = 26196, RequireBuffId = 25655, GroupId = 244 };

        public Services()
        {
            Swap(Skills);
            Swap(Requirements);
            var zones = new ZoneManager(Mock.Of<IWorldManager>().Object);
            SetField(zones, "_zones", new Dictionary<uint, Zone>
            {
                [378] = new() { ZoneKey = 378, GroupId = 133 },
                [382] = new() { ZoneKey = 382, GroupId = 133 },
                [379] = new() { ZoneKey = 379, GroupId = 134 }
            });
            SetField(zones, "_groups", new Dictionary<uint, ZoneGroup>
            {
                [133] = new() { Id = 133, BuffId = 26390 },
                [134] = new() { Id = 134 }
            });
            Swap(zones);
            Swap(new TaskManager(Mock.Of<ITickManager>().Object));
            Swap(new EffectTaskManager(Mock.Of<ITaskManager>().Object));
            var data = new BuffGameData();
            SetField(data, "_buffModifiers", new Dictionary<uint, List<BuffModifier>>());
            Swap(data);
            using var db = new SqliteConnection("Data Source=:memory:"); db.Open();
            using var cmd = db.CreateCommand();
            // r575 native paired quest gates: remove only outside Progress, add only in Progress.
            cmd.CommandText = """
                CREATE TABLE unit_reqs(id,owner_id,owner_type,kind_id,value1,value2,enable,value3,display_msg);
                INSERT INTO unit_reqs VALUES(69741,4486,'BuffTickEffect',72,10056,0,'t',0,'t');
                INSERT INTO unit_reqs VALUES(69796,4489,'BuffTickEffect',32,10056,0,'t',0,'t');
                INSERT INTO unit_reqs VALUES(1,9000,'BuffTickEffect',1,55,0,'t',0,'f');
                INSERT INTO unit_reqs VALUES(2,9000,'BuffTickEffect',32,10056,0,'t',0,'f');
                INSERT INTO unit_reqs VALUES(3,9001,'BuffTickEffect',1,99,0,'f',0,'f');
                INSERT INTO unit_reqs VALUES(69740,4479,'BuffTickEffect',130,3,1,'t',5,'t');
                INSERT INTO unit_reqs VALUES(69761,4479,'BuffTickEffect',32,10056,0,'t',0,'t');
                INSERT INTO unit_reqs VALUES(70021,4479,'BuffTickEffect',97,0,1,'t',0,'t');
                CREATE TABLE zone_score_contents(id,zone_group_id,quest_id);
                CREATE TABLE zone_score_kinds(id,content_id,max_score,db_save);
                CREATE TABLE zone_score_levels(kind_id,level,req_score);
                INSERT INTO zone_score_contents VALUES(2,133,10056);
                INSERT INTO zone_score_kinds VALUES(3,2,10064800,'t');
                INSERT INTO zone_score_levels VALUES(3,0,0),(3,5,16900),(3,6,21600);
                """;
            cmd.ExecuteNonQuery();
            cmd.CommandText = "DELETE FROM zone_score_levels;";
            for (var i = 0; i < RankIds.Length; i++)
                cmd.CommandText += $"INSERT INTO zone_score_levels VALUES(3,{i},{RankScores[i]});" +
                    $"INSERT INTO unit_reqs VALUES({80000+i},{4551+i},'BuffTickEffect',130,3,2,'t',{i},'f');";
            cmd.ExecuteNonQuery(); Requirements.Load(db);
            var scoreData = new GardenScoreGameData(); scoreData.Load(db); Swap(scoreData);
            SetField(Skills, "_buffs", new Dictionary<uint, BuffTemplate>
                { [26390] = Environment, [25655] = Patrol, [26196] = Rank });
            SetField(Skills, "_taggedBuffs", new Dictionary<uint, List<uint>> { [4497] = [25655] });
            SetField(Skills, "_types", new Dictionary<uint, EffectType>
            {
                [83663] = new() { ActualId = 4774, Type = "DispelEffect" },
                [83680] = new() { ActualId = 33106, Type = "BuffEffect" },
                [83620] = new() { ActualId = 49093, Type = "SpecialEffect" }
            });
            SetField(Skills, "_effects", new Dictionary<string, Dictionary<uint, EffectTemplate>>
            {
                ["DispelEffect"] = new() { [4774] = new DispelEffect { Id = 4774, BuffTagId = 4497, CureCount = 1 } },
                ["BuffEffect"] = new() { [33106] = new BuffEffect { Id = 33106, Buff = Patrol, Chance = 100, Stack = 1 } },
                ["SpecialEffect"] = new() { [49093] = new SpecialEffect { Id = 49093,
                    SpecialEffectTypeId = SpecialType.ChangeZoneScore, Value1 = 3, Value2 = 1, Value4 = 5 } }
            });
            Environment.TickEffects.Add(new TickEffect { Id = 4486, EffectId = 83663, TargetBuffTagId = 4497 });
            Environment.TickEffects.Add(new TickEffect { Id = 4489, EffectId = 83680, TargetNoBuffTagId = 4497 });
        }

        public void Register(BuffTemplate template) => ReadField<Dictionary<uint, BuffTemplate>>(Skills, "_buffs")[template.Id] = template;

        public void EnableRankTicks()
        {
            for (var i = 0; i < RankIds.Length; i++)
            {
                var template = new BuffTemplate { Id = RankIds[i], GroupId = 244, GroupRank = 0, RequireBuffId = 25655 };
                Register(template);
                var tag = i == 0 ? 4636u : (uint)(4484 + i);
                ReadField<Dictionary<uint, List<uint>>>(Skills, "_taggedBuffs")[tag] = [template.Id];
                var effectId = (uint)(84383 + i); var actualId = (uint)(33542 + i);
                ReadField<Dictionary<uint, EffectType>>(Skills, "_types")[effectId] = new() { ActualId = actualId, Type = "BuffEffect" };
                ReadField<Dictionary<string, Dictionary<uint, EffectTemplate>>>(Skills, "_effects")["BuffEffect"][actualId] =
                    new BuffEffect { Id = actualId, Buff = template, Chance = 100, Stack = 1 };
                Patrol.TickEffects.Add(new TickEffect { Id = (uint)(4551 + i), EffectId = effectId, TargetNoBuffTagId = tag });
            }
        }

        private void Swap<T>(T value) where T : class
        {
            var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
            _saved.Add((field, field.GetValue(null)!)); field.SetValue(null, value);
        }
        public void Dispose()
        {
            foreach (var (field, value) in _saved) field.SetValue(null, value);
        }
    }

    private static void SetField(object target, string name, object value) =>
        target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);
    private static T ReadField<T>(object target, string name) =>
        (T)target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(target)!;

    [Test]
    public async Task RankTick_ReplacesEveryPreviousLevel_AndKeepsOnlyCurrentMember()
    {
        using var services = new Services(); services.EnableRankTicks();
        var player = Player(true);
        player.ReconcileZoneBuffs(0, 378);
        services.Environment.TimeToTimeApply(player, player, player.Buffs.GetEffectFromBuffId(26390));
        var patrol = player.Buffs.GetEffectFromBuffId(25655);
        var task = new AAEmu.Game.Models.Tasks.Skills.DispelTask(patrol);
        foreach (var level in Enumerable.Range(0, 13).Concat([4, 0, 12]))
        {
            player.GardenScore.Add(RankScores[level] - player.GardenScore.Score);
            task.Execute();
            for (var candidate = 0; candidate < RankIds.Length; candidate++)
                await Assert.That(player.Buffs.CheckBuff(RankIds[candidate])).IsEqualTo(candidate == level);
            var rank = player.Buffs.GetEffectFromBuffId(RankIds[level]);
            task.Execute();
            await Assert.That(player.Buffs.GetEffectFromBuffId(RankIds[level])).IsSameReferenceAs(rank);
            await Assert.That(player.Buffs.GetEffectFromBuffId(25655)).IsSameReferenceAs(patrol);
        }
    }

    [Test]
    public async Task GroupPriority_ProtectsHigherRank_AndLeavesUngroupedBuffsAlone()
    {
        using var services = new Services(); var player = Player(true);
        var lower = new BuffTemplate { Id = 242, GroupId = 10, GroupRank = 1 };
        var higher = new BuffTemplate { Id = 514, GroupId = 10, GroupRank = 2 };
        services.Register(lower); services.Register(higher);
        foreach (var template in new[] { services.Environment, lower, higher, lower })
            player.Buffs.AddBuff(new Buff(player, player, new SkillCasterUnit(player.ObjId), template, null, DateTime.UtcNow));
        await Assert.That(player.Buffs.CheckBuff(242)).IsFalse();
        await Assert.That(player.Buffs.CheckBuff(514)).IsTrue();
        await Assert.That(player.Buffs.CheckBuff(26390)).IsTrue();
    }

    private static QuietCharacter Player(bool progress)
    {
        var player = new QuietCharacter { ObjId = 1762, Level = 55 };
        player.Quests = new CharacterQuests(player);
        if (progress)
        {
            var quest = new Quest(null, player, null, null, null, null, null);
            SetField(quest, "_step", QuestComponentKind.Progress);
            player.Quests.ActiveQuests.Add(10056, quest);
        }
        return player;
    }

    [Test]
    public async Task NativePatrolTick_AddsFivePointsThroughLevelFive_AndRejectsDeadOrInactive()
    {
        using var services = new Services();
        services.Patrol.TickEffects.Add(new TickEffect { Id = 4479, EffectId = 83620 });
        var player = Player(true); player.Hp = 100;
        var patrol = new Buff(player, player, new SkillCasterUnit(player.ObjId), services.Patrol, null, DateTime.UtcNow);
        player.Buffs.AddBuff(patrol);
        var task = new AAEmu.Game.Models.Tasks.Skills.DispelTask(patrol);
        task.Execute();
        await Assert.That(player.GardenScore.Score).IsEqualTo(5);
        player.GardenScore.Add(16900 - 5);
        task.Execute();
        await Assert.That(player.GardenScore.Score).IsEqualTo(16905);
        player.GardenScore.Add(21600 - 16905);
        task.Execute();
        await Assert.That(player.GardenScore.Score).IsEqualTo(21600);
        player.GardenScore.ResetForQuest(10056); player.Hp = 0;
        task.Execute();
        await Assert.That(player.GardenScore.Score).IsEqualTo(0);
        player.Hp = 100; player.Quests.ActiveQuests.Clear();
        task.Execute();
        await Assert.That(player.GardenScore.Score).IsEqualTo(0);
    }

    [Test]
    public async Task ZoneBuff_WaitsForSelectedCharacter_ThenTicksAndSurvivesGardenPartitionChange()
    {
        using var services = new Services();
        var player = new QuietCharacter();
        player.ReconcileZoneBuffs(0, 378);
        await Assert.That(player.Buffs.CheckBuff(26390)).IsFalse();
        player.ObjId = 1762;
        player.ReconcileZoneBuffs(0, 378);
        await Assert.That(player.Buffs.CheckBuff(26390)).IsFalse();
        player.Quests = new CharacterQuests(player);
        var quest = new Quest(null, player, null, null, null, null, null);
        SetField(quest, "_step", QuestComponentKind.Progress);
        player.Quests.ActiveQuests.Add(10056, quest);
        player.ReconcileZoneBuffs(0, 378);
        var environment = player.Buffs.GetEffectFromBuffId(26390);
        await Assert.That(environment).IsNotNull();
        await Assert.That(environment.SkillCaster.ObjId).IsEqualTo(1762u);
        // Exercise the scheduler callback, not a direct call to the tick template.
        new AAEmu.Game.Models.Tasks.Skills.DispelTask(environment).Execute();
        await Assert.That(player.Buffs.CheckBuff(25655)).IsTrue();
        player.ReconcileZoneBuffs(378, 382);
        await Assert.That(player.Buffs.GetEffectFromBuffId(26390)).IsSameReferenceAs(environment);
        player.ReconcileZoneBuffs(382, 379);
        await Assert.That(player.Buffs.CheckBuff(26390)).IsFalse();
        await Assert.That(player.Buffs.CheckBuff(25655)).IsFalse();
    }

    [Test]
    public async Task GardenTicks_KeepPatrolAndRankInstances_UntilQuestStops()
    {
        using var services = new Services();
        var player = Player(true);
        var caster = new SkillCasterUnit(player.ObjId);
        var environment = new Buff(player, player, caster, services.Environment, null, DateTime.UtcNow) { Passive = true };
        player.Buffs.AddBuff(environment);
        services.Environment.TimeToTimeApply(player, player, environment);
        var patrol = player.Buffs.GetEffectFromBuffId(25655);
        await Assert.That(patrol).IsNotNull();
        player.Buffs.AddBuff(new Buff(player, player, caster, services.Rank, null, DateTime.UtcNow) { Passive = true });
        var rank = player.Buffs.GetEffectFromBuffId(26196);
        for (var i = 0; i < 120; i++)
            services.Environment.TimeToTimeApply(player, player, environment);
        await Assert.That(ReferenceEquals(player.Buffs.GetEffectFromBuffId(25655), patrol)).IsTrue();
        await Assert.That(ReferenceEquals(player.Buffs.GetEffectFromBuffId(26196), rank)).IsTrue();
        player.Quests.ActiveQuests.Remove(10056);
        services.Environment.TimeToTimeApply(player, player, environment);
        await Assert.That(player.Buffs.CheckBuff(25655)).IsFalse();
        await Assert.That(player.Buffs.CheckBuff(26196)).IsFalse();
    }

    [Test]
    public async Task QuestGates_RejectNpcAndPlayerWithoutQuest()
    {
        using var services = new Services();
        foreach (var recipient in new BaseUnit[] { new Unit(), Player(false) })
        {
            var environment = new Buff(recipient, recipient, new SkillCasterUnit(), services.Environment, null, DateTime.UtcNow);
            services.Environment.TimeToTimeApply(recipient, recipient, environment);
            await Assert.That(recipient.Buffs.CheckBuff(25655)).IsFalse();
            await Assert.That(services.Requirements.CanApplyBuffTickEffect(services.Environment.TickEffects[1], recipient)).IsFalse();
        }
    }

    [Test]
    public async Task Conditions_RespectAndOrDisabledAndUngatedRows()
    {
        using var services = new Services();
        var player = Player(false);
        var effect = new TickEffect { Id = 9000 };
        await Assert.That(services.Requirements.CanApplyBuffTickEffect(effect, player)).IsFalse();
        effect.OrUnitReqs = true;
        await Assert.That(services.Requirements.CanApplyBuffTickEffect(effect, player)).IsTrue();
        await Assert.That(services.Requirements.CanApplyBuffTickEffect(new TickEffect { Id = 9001 }, player)).IsTrue();
        await Assert.That(services.Requirements.CanApplyBuffTickEffect(new TickEffect { Id = 9999 }, player)).IsTrue();
    }
}
