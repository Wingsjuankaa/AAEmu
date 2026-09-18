using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using Microsoft.Extensions.Time.Testing;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class ClientSkillComboTests
{
    private static SkillTemplate Link(uint id, uint next, int window) => new()
    {
        Id = id,
        Effects = [new SkillEffect
        {
            StartLevel = 1, EndLevel = 99, Chance = 100,
            Friendly = true, NonFriendly = true, Front = true, Back = true,
            Template = new SpecialEffect { SpecialEffectTypeId = SpecialType.Combo, Value1 = (int)next, Value2 = window }
        }]
    };

    [Test]
    [Arguments(18132u, 18134u, 18131u, 1000)]
    [Arguments(13282u, 32040u, 32049u, 1500)]
    public async Task RetailChains_RequireAcceptedPredecessor_ConsumeEachStep(uint root, uint second, uint third, int window)
    {
        var clock = new FakeTimeProvider();
        var combo = new ClientSkillCombo(clock);
        bool Owns(uint id) => id == root;
        await Assert.That(combo.CanContinue(second, Owns)).IsFalse();
        combo.Accepted(Link(root, second, window), 55, Owns);
        await Assert.That(combo.CanContinue(third, Owns)).IsFalse();
        clock.Advance(TimeSpan.FromMilliseconds(500));
        await Assert.That(combo.CanContinue(second, Owns)).IsTrue();
        // A rejected attempt does not advance or refresh the window.
        await Assert.That(combo.CanContinue(second, Owns)).IsTrue();
        combo.Accepted(Link(second, third, window), 55, Owns);
        await Assert.That(combo.CanContinue(second, Owns)).IsFalse();
        await Assert.That(combo.CanContinue(third, Owns)).IsTrue();
        combo.Accepted(new SkillTemplate { Id = third }, 55, Owns);
        await Assert.That(combo.CanContinue(third, Owns)).IsFalse();
    }

    [Test]
    public async Task ExpiredWindow_CannotBeRevivedByAnUnlearnedChild()
    {
        var clock = new FakeTimeProvider();
        var combo = new ClientSkillCombo(clock);
        bool Owns(uint id) => id == 18132;
        combo.Accepted(Link(18132, 18134, 1000), 55, Owns);
        clock.Advance(TimeSpan.FromMilliseconds(999));
        await Assert.That(combo.CanContinue(18134, Owns)).IsTrue();
        clock.Advance(TimeSpan.FromMilliseconds(1));
        await Assert.That(combo.CanContinue(18134, Owns)).IsFalse();
        combo.Accepted(Link(18134, 18131, 1000), 55, Owns);
        await Assert.That(combo.CanContinue(18131, Owns)).IsFalse();
    }

    [Test]
    public async Task Expiry_IncludesNativeCombatSyncOffset()
    {
        var clock = new FakeTimeProvider();
        var combo = new ClientSkillCombo(clock);
        var root = Link(18132, 18134, 1000);
        root.FireAnim = new AAEmu.Game.Models.Game.Animation.Anim { CombatSyncTime = 300 };
        bool Owns(uint id) => id == root.Id;
        combo.Accepted(root, 55, Owns);
        clock.Advance(TimeSpan.FromMilliseconds(1299));
        await Assert.That(combo.CanContinue(18134, Owns)).IsTrue();
        clock.Advance(TimeSpan.FromMilliseconds(1));
        await Assert.That(combo.CanContinue(18134, Owns)).IsFalse();
    }

    [Test]
    public async Task OtherAcceptedCastOrLostRoot_InvalidatesChain()
    {
        var combo = new ClientSkillCombo();
        var owned = new HashSet<uint> { 18132, 13282 };
        combo.Accepted(Link(18132, 18134, 1000), 55, owned.Contains);
        owned.Remove(18132);
        await Assert.That(combo.CanContinue(18134, owned.Contains)).IsFalse();
        owned.Add(18132);
        combo.Accepted(Link(13282, 32040, 1500), 55, owned.Contains);
        await Assert.That(combo.CanContinue(18134, owned.Contains)).IsFalse();
        await Assert.That(combo.CanContinue(32040, owned.Contains)).IsTrue();
        combo.Accepted(null, 55, owned.Contains); // mount / item / different caster
        await Assert.That(combo.CanContinue(32040, owned.Contains)).IsFalse();
    }

    [Test]
    public async Task ConditionalAmbiguousOrOutOfLevelRows_DoNotGrantPermission()
    {
        var conditional = Link(18132, 18134, 1000);
        conditional.Effects[0].SourceBuffTagId = 3105;
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(conditional, 55, out _, out _)).IsFalse();
        var random = Link(18132, 18134, 1000);
        random.Effects[0].Chance = 50;
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(random, 55, out _, out _)).IsFalse();
        var ambiguous = Link(18132, 18134, 1000);
        ambiguous.Effects.AddRange(Link(18132, 18131, 1000).Effects);
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(ambiguous, 55, out _, out _)).IsFalse();
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(Link(18132, 18134, 1000), 100, out _, out _)).IsFalse();
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(Link(18132, 18134, 0), 55, out _, out _)).IsFalse();
        var casting = Link(18132, 18134, 1000);
        casting.CastingTime = 2000;
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(casting, 55, out _, out _)).IsFalse();
        casting.CastingTime = 0;
        casting.ChannelingTime = 2000;
        await Assert.That(ClientSkillCombo.TryGetUnconditionalLink(casting, 55, out _, out _)).IsFalse();
    }

    [Test]
    public async Task CharacterAdmission_OnlyOwnUnit_WithoutLearningOrSpendingPoints()
    {
        var owner = new Character(null) { ObjId = 100, Level = 55 };
        owner.Skills = new CharacterSkills(owner);
        var root = Link(18132, 18134, 1000);
        owner.Skills.Skills.Add(root.Id, new Skill { Id = root.Id, Template = root });
        var ownCaster = new SkillCasterUnit(owner.ObjId);
        owner.Skills.RecordAcceptedClientCast(root, ownCaster);
        await Assert.That(owner.Skills.CanContinueClientCombo(18134, ownCaster)).IsTrue();
        await Assert.That(owner.Skills.CanContinueClientCombo(18134, new SkillCasterUnit(101))).IsFalse();
        await Assert.That(owner.Skills.CanContinueClientCombo(18134, new SkillCasterMount(owner.ObjId))).IsFalse();
        await Assert.That(owner.Skills.HasSkill(18134)).IsFalse();
        await Assert.That(owner.Skills.Skills.Keys).IsEquivalentTo(new uint[] { 18132 });
        owner.Skills.Skills.Clear(); // ability reset
        await Assert.That(owner.Skills.CanContinueClientCombo(18134, ownCaster)).IsFalse();
        var relogged = new Character(null) { ObjId = 100, Level = 55 };
        relogged.Skills = new CharacterSkills(relogged);
        await Assert.That(relogged.Skills.CanContinueClientCombo(18134, ownCaster)).IsFalse();
    }
}
