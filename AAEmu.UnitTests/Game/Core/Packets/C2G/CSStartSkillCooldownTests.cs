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
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.World;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Core.Packets.C2G;

[NotInParallel]
public class CSStartSkillCooldownTests
{
    [Test]
    [Arguments(true, 14835u, 14836u, 220, true)]
    [Arguments(false, 14835u, 14836u, 220, true)]
    [Arguments(true, 18132u, 18134u, 500, true)]
    [Arguments(false, 18132u, 18134u, 500, true)]
    [Arguments(true, 13282u, 32040u, 500, true)]
    [Arguments(false, 13282u, 32040u, 500, true)]
    [Arguments(true, 14810u, 14811u, 250, true)]
    [Arguments(false, 14810u, 14811u, 250, true)]
    [Arguments(true, 18125u, 18126u, 500, true)]
    [Arguments(false, 18125u, 18126u, 500, true)]
    [Arguments(true, 10752u, 24894u, 10, false)]
    [Arguments(false, 10752u, 24894u, 10, false)]
    public async Task Read_CooldownRejectedRootAndContinuation_ReplyWithoutConsumingChainOrResources(
        bool zoneAuthority, uint rootId, uint childId, int customGcd, bool startAutoAttack)
    {
        using var skills = new SingletonScope<SkillManager>(TestManagers.CreateSkillManager());
        using var requirements = new SingletonScope<UnitRequirementsGameData>(new());
        using var heirs = new SingletonScope<HeirGameData>(new());
        using var worlds = new SingletonScope<WorldManager>(new(null, null, null, null, null));
        var world = new WorldInstance(new WorldTemplate(), 0, true, 0);
        ((ConcurrentDictionary<uint, WorldInstance>)typeof(WorldManager)
            .GetField("_worlds", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(WorldManager.Instance)!)
            .TryAdd(world.Id, world);
        var sent = new List<byte[]>();
        var session = Mock.Of<ISession>();
        session.SendPacket(Any<byte[]>()).Callback((byte[] bytes) => sent.Add(bytes));
        var connection = new GameConnection(session.Object);
        var owner = new Character(null) { ObjId = 100, Level = 55, Hp = 100, Mp = 100, Connection = connection };
        owner.ParentWorld = world;
        owner.Skills = new CharacterSkills(owner);
        connection.ActiveChar = owner;
        var root = Template(rootId, customGcd, startAutoAttack);
        root.Effects = [new SkillEffect
        {
            StartLevel = 1, EndLevel = 99, Chance = 100,
            Friendly = true, NonFriendly = true, Front = true, Back = true,
            Template = new SpecialEffect { SpecialEffectTypeId = SpecialType.Combo, Value1 = (int)childId, Value2 = 1000 }
        }];
        var child = Template(childId, customGcd, startAutoAttack);
        typeof(SkillManager).GetField("_skills", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(SkillManager.Instance, new Dictionary<uint, SkillTemplate> { [rootId] = root, [childId] = child });
        owner.Skills.Skills.Add(rootId, new Skill(root));
        var caster = new SkillCasterUnit(owner.ObjId);
        var target = new SkillCastUnitTarget(999);
        owner.Skills.RecordAcceptedClientCast(root, caster);
        var gcd = owner.GlobalCooldown = DateTime.UtcNow.AddMinutes(1);
        var lastUsed = owner.SkillLastUsed = DateTime.UtcNow.AddMinutes(-1);
        var previousAuthority = WorldIntegration.ZoneAuthority;
        var previousForceLocal = Environment.GetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS");
        try
        {
            WorldIntegration.ZoneAuthority = zoneAuthority;
            Environment.SetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS", null);
            // Repeat rejection too: neither a lost response nor a rejected attempt
            // may consume/refresh the authorization for the pending child.
            foreach (var template in new[] { root, child, child })
            {
                sent.Clear();
                var request = new PacketStream().Write(template.Id).Write(caster).Write(target)
                    .Write((byte)SkillObjectType.None).Write((byte)0);
                request.Pos = 0;
                new CSStartSkillPacket { Connection = connection }.Read(request);

                await Assert.That(sent.Count).IsEqualTo(1);
                var expected = new SCSkillStartedPacket(template.Id, 0, caster, target, new Skill(template), new SkillObject())
                {
                    Connection = connection, RealCastTimeDiv10 = 0, BaseCastTimeDiv10 = 0
                };
                expected.SetSkillResult(SkillResult.CooldownTime);
                await Assert.That(Convert.ToHexString(sent[0])).IsEqualTo(Convert.ToHexString(expected.Encode().GetBytes()));
                await Assert.That(owner.GlobalCooldown).IsEqualTo(gcd);
                await Assert.That(owner.SkillLastUsed).IsEqualTo(lastUsed);
                await Assert.That(owner.Mp).IsEqualTo(100);
                await Assert.That(owner.Skills.CanContinueClientCombo(childId, caster)).IsTrue();
                await Assert.That(owner.Skills.HasSkill(childId)).IsFalse();
            }
        }
        finally
        {
            WorldIntegration.ZoneAuthority = previousAuthority;
            Environment.SetEnvironmentVariable("AAEMU_FORCE_LOCAL_SKILLS", previousForceLocal);
        }
    }

    private static SkillTemplate Template(uint id, int gcd, bool startAutoAttack) => new()
    {
        Id = id, AbilityId = (AbilityType)1, UseConditionBits = 1, CustomGcd = gcd,
        StartAutoAttack = startAutoAttack, TargetType = SkillTargetType.AnyUnit
    };
}
