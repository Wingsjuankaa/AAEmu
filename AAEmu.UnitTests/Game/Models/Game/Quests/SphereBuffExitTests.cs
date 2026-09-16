using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Buffs.Triggers;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Spheres;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class SphereBuffExitTests
{
    private readonly List<(FieldInfo Field, object Value)> _saved = [];
    private readonly Dictionary<uint, SphereBuffs> _details = [];
    private static readonly MethodInfo Apply = typeof(CharacterQuests)
        .GetMethod("ApplySphereBuff", BindingFlags.NonPublic | BindingFlags.Instance)!;

    private void Swap<T>(T value) where T : class
    {
        var field = typeof(Singleton<T>).GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
        _saved.Add((field, field.GetValue(null)));
        field.SetValue(null, value);
    }

    [Before(Test)]
    public void Setup()
    {
        var data = new SphereGameData();
        typeof(SphereGameData).GetField("_sphereBuffs", BindingFlags.NonPublic | BindingFlags.Instance)!
            .SetValue(data, _details);
        Swap(data);
        Swap(new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
    }

    [After(Test)]
    public void Cleanup()
    {
        foreach (var (field, value) in _saved) field.SetValue(null, value);
    }

    private sealed class CaptureEffect : EffectTemplate
    {
        public int Count;
        public override bool OnActionTime => false;
        public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source, SkillObject skillObject,
            DateTime time, CompressedGamePackets packetBuilder = null) => Count++;
    }

    [Test]
    public async Task FirstNebeNoteSurvivesExitAndAuthorizesSecondNoteTrigger()
    {
        // r575 sphere2983/detail87: no exit removal. Trigger13371 on note26249
        // requires tag4658 (note26248) before producing the combined state26255.
        _details[87] = new SphereBuffs { Id = 87, BuffId = 26248 };
        var buffs = Mock.Of<IBuffs>();
        var owner = new Character(null) { Buffs = buffs.Object };
        var effect = new CaptureEffect();
        var buff = new Buff(owner, owner, new SkillCasterUnit(owner.ObjId),
            new BuffTemplate { Id = 26249 }, null, DateTime.UtcNow);
        var trigger = new BuffTrigger(buff, new BuffTriggerTemplate
        {
            Id = 13371, OwnerBuffTagId = 4658, Effect = effect
        });

        buffs.CheckBuffTag(4658).Returns(false);
        trigger.Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Count).IsEqualTo(0); // The preceding note is required.

        buffs.CheckBuff(26248).Returns(true);
        buffs.CheckBuffTag(4658).Returns(true);
        buffs.RemoveBuff(26248, true).Callback((uint id, bool notify) =>
        {
            buffs.CheckBuff(id).Returns(false);
            buffs.CheckBuffTag(4658).Returns(false);
        });
        var quests = new CharacterQuests(owner);
        Apply.Invoke(quests, [87u, false]);
        Apply.Invoke(quests, [87u, false]); // Repeated exits must not erase progress either.
        trigger.Execute(owner, EventArgs.Empty);
        await Assert.That(effect.Count).IsEqualTo(1);
        buffs.RemoveBuff(26248, true).WasCalled(Times.Never);
    }

    [Test]
    [Arguments(5u, 13817u, false)] // Moored: explicit removal, mount routing unchanged.
    [Arguments(15u, 13789u, true)] // Character/pet shipyard permission.
    [Arguments(94u, 26261u, false)] // Nebe's final check area, unlike its notes.
    public void ExplicitExitRemovalStillRuns(uint detailId, uint buffId, bool andPet)
    {
        _details[detailId] = new SphereBuffs
        {
            Id = detailId, BuffId = buffId, RemoveOnLeaveBuffId = buffId, AndPet = andPet
        };
        var buffs = Mock.Of<IBuffs>();
        buffs.CheckBuff(buffId).Returns(true);
        var owner = new Character(null) { Buffs = buffs.Object };
        Apply.Invoke(new CharacterQuests(owner), [detailId, false]);
        buffs.RemoveBuff(buffId, true).WasCalled(Times.Once);
    }

    [Test]
    public void ExitRemovesOnlyTheExplicitTargetWhenItDiffersFromTheEntryBuff()
    {
        _details[1] = new SphereBuffs { Id = 1, BuffId = 100, RemoveOnLeaveBuffId = 200 };
        var buffs = Mock.Of<IBuffs>();
        buffs.CheckBuff(100).Returns(true);
        buffs.CheckBuff(200).Returns(true);
        Apply.Invoke(new CharacterQuests(new Character(null) { Buffs = buffs.Object }), [1u, false]);
        buffs.RemoveBuff(200, true).WasCalled(Times.Once);
        buffs.RemoveBuff(100, true).WasCalled(Times.Never);
    }
}
