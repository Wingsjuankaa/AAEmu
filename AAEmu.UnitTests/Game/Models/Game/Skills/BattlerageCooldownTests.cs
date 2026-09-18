using System.Reflection;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class BattlerageCooldownTests
{
    private object _previous;
    private static readonly FieldInfo InstanceField = typeof(Singleton<SkillManager>)
        .GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;

    [Before(Test)]
    public void Setup()
    {
        _previous = InstanceField.GetValue(null);
        var manager = new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object);
        InstanceField.SetValue(null, manager);
        // r575 tag 415 includes Charge, Sunder Earth and its Quake variant.
        Set(manager, "_skills", new Dictionary<uint, SkillTemplate>
        {
            [11918] = new() { Id = 11918 },
            [10644] = new() { Id = 10644, CooldownTags = [4156] },
            [41217] = new() { Id = 41217, CooldownTags = [4156] },
            [999] = new() { Id = 999, CooldownTags = [5000, 5001, 5002] }
        });
        Set(manager, "_taggedSkills", new Dictionary<uint, List<uint>> { [415] = [11918, 10644, 41217] });
    }

    private static void Set(SkillManager manager, string name, object value) =>
        typeof(SkillManager).GetField(name, BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(manager, value);

    [After(Test)]
    public void Cleanup() => InstanceField.SetValue(null, _previous);

    private static void Apply(Character owner, int skill, int tag, int gcd, int skillTags, int taggedSkills, int taggedSkillTags)
    {
        // Exercise the seven-value dispatch used by BuffTrigger -> SpecialEffect,
        // rather than invoking the cooldown storage in isolation.
        new SpecialEffect
        {
            SpecialEffectTypeId = SpecialType.ResetCooldown,
            Value1 = skill, Value2 = tag, Value3 = gcd, Value4 = skillTags,
            Value5 = taggedSkills, Value6 = taggedSkillTags
        }.Apply(owner, null, owner, null, null, new EffectSource(new Skill(new SkillTemplate())), null, DateTime.UtcNow);
    }

    [Test]
    public async Task NativeDeflect4636_ResetsTaggedSkillsAndTheirGroupsOnly()
    {
        var owner = new Character(null) { GlobalCooldown = DateTime.UtcNow.AddMinutes(1) };
        owner.Cooldowns.AddCooldown(11918, 60000);
        owner.Cooldowns.AddCooldown(10644, 60000, [4156]);
        owner.Cooldowns.AddCooldown(41217, 60000, [4156]);
        owner.Cooldowns.AddCooldown(999, 60000, [5000]);
        owner.Cooldowns.AddCooldown(415, 60000); // A skill id must not alias the tag id.
        // Full r575 special_effects 4636: 0,415,1,0,1,1,0.
        Apply(owner, 0, 415, 1, 0, 1, 1);
        foreach (var id in new uint[] { 11918, 10644, 41217 })
            await Assert.That(owner.Cooldowns.CheckCooldown(id)).IsFalse();
        await Assert.That(owner.Cooldowns.CheckTagCooldown([4156])).IsFalse();
        await Assert.That(owner.Cooldowns.CheckCooldown(999, [5000])).IsTrue();
        await Assert.That(owner.Cooldowns.CheckCooldown(415)).IsTrue();
        await Assert.That(owner.GlobalCooldown < DateTime.UtcNow).IsTrue();
    }

    [Test]
    [Arguments(0)]
    [Arguments(1)]
    public async Task ResetSkillTagsFlag_ControlsAllThreeGroups(int resetTags)
    {
        var owner = new Character(null) { GlobalCooldown = DateTime.UtcNow.AddMinutes(1) };
        owner.Cooldowns.AddCooldown(999, 60000, [5000, 5001, 5002]);
        owner.Cooldowns.AddCooldown(10644, 60000, [4156]);
        Apply(owner, 999, 0, 0, resetTags, 0, 0);
        await Assert.That(owner.Cooldowns.CheckCooldown(999)).IsFalse();
        foreach (var tag in new[] { 5000, 5001, 5002 })
            await Assert.That(owner.Cooldowns.CheckTagCooldown([tag])).IsEqualTo(resetTags == 0);
        await Assert.That(owner.Cooldowns.CheckCooldown(10644, [4156])).IsTrue();
        await Assert.That(owner.GlobalCooldown > DateTime.UtcNow).IsTrue();
    }

    [Test]
    [Arguments(0, 0)]
    [Arguments(0, 1)]
    [Arguments(1, 0)]
    [Arguments(1, 1)]
    public async Task TaggedSkillFlags_DoNotBroadenTheSelection(int resetSkills, int resetGroups)
    {
        var owner = new Character(null);
        owner.Cooldowns.AddCooldown(10644, 60000, [4156]);
        Apply(owner, 0, 415, 0, 0, resetSkills, resetGroups);
        await Assert.That(owner.Cooldowns.CheckCooldown(10644)).IsEqualTo(resetSkills == 0);
        await Assert.That(owner.Cooldowns.CheckTagCooldown([4156])).IsEqualTo(resetSkills == 0 || resetGroups == 0);
    }

    [Test]
    public async Task NativeDeflectPacket_PreservesAllFourResetFlags()
    {
        var owner = new Character(null) { ObjId = 100 };
        var packet = ResetCooldown.ApplyReset(owner, 0, 415, true, false, true, true);
        var stream = new PacketStream(packet.Write(new PacketStream()).GetBytes());
        await Assert.That(stream.ReadBc()).IsEqualTo(owner.ObjId);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(415u);
        await Assert.That(stream.ReadBoolean()).IsTrue();  // gc
        await Assert.That(stream.ReadBoolean()).IsFalse(); // rstc
        await Assert.That(stream.ReadBoolean()).IsTrue();  // rtsc: reset tagged skills
        await Assert.That(stream.ReadBoolean()).IsTrue();  // rtstc: also reset their tags
        await Assert.That(stream.Pos).IsEqualTo(stream.Count);
    }
}
