using AAEmu.Game.Core.Managers;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class ClientSkillComboAdmissionTests
{
    [Test]
    [Arguments(true, 18134u, false, false, SkillResult.CooldownTime)]
    [Arguments(false, 18134u, false, false, SkillResult.CooldownTime)]
    [Arguments(true, 18131u, false, false, SkillResult.CooldownTime)]
    [Arguments(true, 18132u, false, false, SkillResult.CooldownTime)]
    [Arguments(true, 18134u, true, false, SkillResult.CooldownTime)]
    [Arguments(true, 18134u, false, true, SkillResult.CooldownTime)]
    public async Task Use_LiveClientContinuationDoesNotBypassActiveSharedCooldown(
        bool clientRequested, uint incomingId, bool ownCooldown, bool tagCooldown, SkillResult expected)
    {
        using var skills = new SingletonScope<SkillManager>(TestManagers.CreateSkillManager());
        using var requirements = new SingletonScope<UnitRequirementsGameData>(new());
        var owner = new Character(null) { ObjId = 100, Level = 55, Hp = 100 };
        owner.Skills = new CharacterSkills(owner);
        var root = new SkillTemplate
        {
            Id = 18132,
            Effects = [new SkillEffect
            {
                StartLevel = 1, EndLevel = 99, Chance = 100,
                Friendly = true, NonFriendly = true, Front = true, Back = true,
                Template = new SpecialEffect { SpecialEffectTypeId = SpecialType.Combo, Value1 = 18134, Value2 = 1000 }
            }]
        };
        owner.Skills.Skills.Add(root.Id, new Skill { Id = root.Id, Template = root });
        var caster = new SkillCasterUnit(owner.ObjId);
        owner.Skills.RecordAcceptedClientCast(root, caster);
        owner.GlobalCooldown = DateTime.UtcNow.AddMinutes(1);
        owner.SkillLastUsed = DateTime.UtcNow.AddMinutes(1);
        var incoming = new Skill(new SkillTemplate { Id = incomingId, UseConditionBits = 1, CustomGcd = 500, CooldownTags = [123] });
        if (ownCooldown)
            owner.Cooldowns.AddCooldown(incomingId, 60000);
        if (tagCooldown)
            owner.Cooldowns.AddCooldown(999999u, 60000, [123]);

        // Null target deliberately stops at the next validation gate, before
        // any cast, mana charge or world/Zone side effect can run.
        var result = incoming.Use(owner, caster, null, null, false, out _, out _, clientRequested);

        await Assert.That(result).IsEqualTo(expected);
        await Assert.That(owner.Skills.CanContinueClientCombo(18134, caster)).IsTrue();
        await Assert.That(owner.Skills.HasSkill(18134)).IsFalse();
        await Assert.That(owner.GlobalCooldown > DateTime.UtcNow).IsTrue();
    }

    [Test]
    [Arguments(18132u, 18134u, 500, false, false, SkillResult.NoTarget)]
    [Arguments(13282u, 32040u, 500, false, false, SkillResult.NoTarget)]
    [Arguments(14835u, 14836u, 220, false, false, SkillResult.NoTarget)]
    [Arguments(14810u, 14811u, 250, false, false, SkillResult.NoTarget)]
    [Arguments(18125u, 18126u, 500, false, false, SkillResult.NoTarget)]
    [Arguments(10752u, 24894u, 10, false, false, SkillResult.NoTarget)]
    [Arguments(18132u, 18134u, 500, true, false, SkillResult.CooldownTime)]
    [Arguments(18132u, 18134u, 500, false, true, SkillResult.CooldownTime)]
    public async Task Use_AfterSharedCooldown_ContinuationPassesSpamGateButKeepsOwnAndTagCooldowns(
        uint rootId, uint childId, int customGcd, bool ownCooldown, bool tagCooldown, SkillResult expected)
    {
        using var skills = new SingletonScope<SkillManager>(TestManagers.CreateSkillManager());
        using var requirements = new SingletonScope<UnitRequirementsGameData>(new());
        var owner = new Character(null) { ObjId = 100, Level = 55, Hp = 100 };
        owner.Skills = new CharacterSkills(owner);
        var root = new SkillTemplate
        {
            Id = rootId,
            Effects = [new SkillEffect
            {
                StartLevel = 1, EndLevel = 99, Chance = 100,
                Friendly = true, NonFriendly = true, Front = true, Back = true,
                Template = new SpecialEffect { SpecialEffectTypeId = SpecialType.Combo, Value1 = (int)childId, Value2 = 1000 }
            }]
        };
        owner.Skills.Skills.Add(root.Id, new Skill(root));
        var caster = new SkillCasterUnit(owner.ObjId);
        owner.Skills.RecordAcceptedClientCast(root, caster);
        owner.GlobalCooldown = DateTime.UtcNow.AddMinutes(-1);
        owner.SkillLastUsed = DateTime.UtcNow.AddMinutes(1);
        var incoming = new Skill(new SkillTemplate { Id = childId, UseConditionBits = 1, CustomGcd = customGcd, CooldownTags = [123] });
        if (ownCooldown)
            owner.Cooldowns.AddCooldown(childId, 60000);
        if (tagCooldown)
            owner.Cooldowns.AddCooldown(999999u, 60000, [123]);

        var result = incoming.Use(owner, caster, null, null, false, out _, out _, clientRequested: true);

        await Assert.That(result).IsEqualTo(expected);
        await Assert.That(owner.Skills.CanContinueClientCombo(childId, caster)).IsTrue();
        await Assert.That(owner.Skills.HasSkill(childId)).IsFalse();
    }
}
