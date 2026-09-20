using System.Collections.Concurrent;
using System.Reflection;

using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Game;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Heirs;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.World;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

[NotInParallel]
public class CSStartSkillHeirTests
{
    [Test]
    [Arguments(true, 36401u, 1000, 400)]
    [Arguments(false, 36401u, 1000, 400)]
    [Arguments(true, 36404u, 2000, 1000)]
    [Arguments(false, 36404u, 2000, 1000)]
    public async Task SelectedAncestralAndItsChain_ReachCastGates_WithoutLearningChildrenOrBypassingCooldown(
        bool zoneAuthority, uint rootId, int window, int customGcd)
    {
        using var skills = new SingletonScope<SkillManager>(TestManagers.CreateSkillManager());
        using var requirements = new SingletonScope<UnitRequirementsGameData>(new());
        using var heirs = new SingletonScope<HeirGameData>(new());
        using var worlds = new SingletonScope<WorldManager>(new(null, null, null, null, null));
        var world = new WorldInstance(new WorldTemplate(), 0, true, 0);
        ((ConcurrentDictionary<uint, WorldInstance>)Field(WorldManager.Instance, "_worlds")).TryAdd(0, world);
        var sent = new List<byte[]>();
        var session = Mock.Of<ISession>();
        session.SendPacket(Any<byte[]>()).Callback((byte[] bytes) => sent.Add(bytes));
        var connection = new GameConnection(session.Object);
        var owner = new Character(null) { ObjId = 100, Level = 55, Hp = 100, Mp = 100, Connection = connection, ParentWorld = world };
        owner.Skills = new CharacterSkills(owner);
        owner.HeirSkills = new CharacterHeirSkills(owner);
        owner.SkillActiveTypes = new CharacterSkillActiveTypes(owner);
        connection.ActiveChar = owner;
        var templates = new Dictionary<uint, SkillTemplate>();
        foreach (var id in new[] { 18132u, 36401u, 36402u, 36403u, 36404u, 36405u, 36406u })
            templates[id] = new SkillTemplate { Id = id, AbilityId = (AbilityType)1, UseConditionBits = 1, CustomGcd = customGcd, TargetType = SkillTargetType.AnyUnit };
        foreach (var id in new[] { rootId, rootId + 1 })
            templates[id].Effects = [new SkillEffect
            {
                StartLevel = 1, EndLevel = 99, Chance = 100,
                Friendly = true, NonFriendly = true, Front = true, Back = true,
                Template = new SpecialEffect { SpecialEffectTypeId = SpecialType.Combo, Value1 = (int)id + 1, Value2 = window }
            }];
        SetField(SkillManager.Instance, "_skills", templates);
        // r575 heir_skills 1 and heir_skill_details 1/2. The selected map is the
        // persisted activation state; this test never writes a database selection.
        SetField(HeirGameData.Instance, "_skillsById", new Dictionary<uint, HeirSkill>
        {
            [1] = new() { Id = 1, SkillId = 18132, Step = 1, Enable = true }
        });
        SetField(HeirGameData.Instance, "_successorsBySkillId", new Dictionary<uint, HeirSkillDetail>
        {
            [36401] = new() { Id = 1, HeirSkillId = 1, SkillId = 36401, Pos = 8, SkillActiveTypeId = SkillActiveType.Active },
            [36404] = new() { Id = 2, HeirSkillId = 1, SkillId = 36404, Pos = 3, SkillActiveTypeId = SkillActiveType.Active }
        });
        var selected = (Dictionary<uint, uint>)Field(owner.HeirSkills, "_activeSuccessors");
        selected[1] = rootId;
        owner.Skills.Skills.Add(18132, new Skill(templates[18132]));
        var caster = new SkillCasterUnit(owner.ObjId);
        var target = new SkillCastUnitTarget(999);
        var previousAuthority = WorldIntegration.ZoneAuthority;
        var previousForceLocal = Environment.GetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS");
        void Request(uint id, uint casterId = 100)
        {
            sent.Clear();
            var body = new PacketStream().Write(id).Write(new SkillCasterUnit(casterId)).Write(target)
                .Write((byte)SkillObjectType.None).Write((byte)0);
            body.Pos = 0;
            new CSStartSkillPacket { Connection = connection }.Read(body);
        }
        async Task ExpectResult(uint id, SkillResult result)
        {
            Request(id);
            await Assert.That(sent.Count).IsGreaterThan(0);
            var expected = new SCSkillStartedPacket(id, 0, caster, target, new Skill(templates[id]), new SkillObject())
            { Connection = connection, RealCastTimeDiv10 = 0, BaseCastTimeDiv10 = 0 };
            expected.SetSkillResult(result);
            await Assert.That(Convert.ToHexString(sent[0])).IsEqualTo(Convert.ToHexString(expected.Encode().GetBytes()));
            await Assert.That(owner.Mp).IsEqualTo(100);
        }
        try
        {
            WorldIntegration.ZoneAuthority = zoneAuthority;
            Environment.SetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS", null);
            var otherRoot = rootId == 36401 ? 36404u : 36401u;
            Request(otherRoot);
            await Assert.That(sent).IsEmpty(); // Unselected Heir root is still refused before dispatch.
            Request(rootId, 101);
            await Assert.That(sent).IsEmpty(); // A selected Heir is not permission to cast as another unit.
            await ExpectResult(rootId + 1, SkillUseConditionRules.UnlearnedSkillResult);

            foreach (var id in new[] { rootId, rootId + 1, rootId + 2 })
            {
                owner.GlobalCooldown = DateTime.UtcNow.AddMinutes(1);
                owner.SkillLastUsed = DateTime.UtcNow.AddMinutes(-1);
                await ExpectResult(id, SkillResult.CooldownTime);
                owner.GlobalCooldown = DateTime.UtcNow.AddMinutes(-1);
                // Missing target stops the real cast before effects/plots. It proves admission,
                // not damage or animation. Seed the accepted predecessor separately below.
                await ExpectResult(id, SkillResult.NoTarget);
                await Assert.That(owner.Skills.HasSkill(id)).IsFalse();
                owner.Skills.RecordAcceptedClientCast(templates[id], caster);
            }
            owner.Skills.RecordAcceptedClientCast(templates[rootId], caster);
            selected[1] = otherRoot;
            await ExpectResult(rootId + 1, SkillUseConditionRules.UnlearnedSkillResult);
            await Assert.That(owner.Skills.Skills.Count).IsEqualTo(1);
        }
        finally
        {
            WorldIntegration.ZoneAuthority = previousAuthority;
            Environment.SetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS", previousForceLocal);
        }
    }

    private static object Field(object target, string name) =>
        target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(target)!;
    private static void SetField(object target, string name, object value) =>
        target.GetType().GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(target, value);
}
