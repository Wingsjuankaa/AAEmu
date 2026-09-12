using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects.Enums;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.DoodadObj.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

[NotInParallel]
public class DoodadAreaSkillTargetTests
{
    private static readonly FieldInfo Manager = typeof(Singleton<DoodadManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previous;
    private static readonly FieldInfo Skills = typeof(Singleton<SkillManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previousSkills;
    private static readonly FieldInfo Models = typeof(Singleton<ModelManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previousModels;

    [Before(Test)]
    public void Setup()
    {
        _previous = Manager.GetValue(null);
        _previousSkills = Skills.GetValue(null);
        _previousModels = Models.GetValue(null);
        var models = new ModelManager();
        typeof(ModelManager).GetField("_modelTypes", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(models, new Dictionary<uint, AAEmu.Game.Models.Game.Models.ModelType>());
        Models.SetValue(null, models);
        Skills.SetValue(null, new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
        var manager = new DoodadManager(null, null, null, null, null, null);
        typeof(DoodadManager).GetField("_funcsByGroups", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<uint, List<DoodadFunc>>());
        typeof(DoodadManager).GetField("_phaseFuncs", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<uint, List<DoodadPhaseFunc>>());
        Manager.SetValue(null, manager);
    }

    [After(Test)]
    public void Cleanup()
    {
        Manager.SetValue(null, _previous);
        Skills.SetValue(null, _previousSkills);
        Models.SetValue(null, _previousModels);
    }

    private sealed class CaptureEffect : EffectTemplate
    {
        public override bool OnActionTime => false;
        public readonly List<(BaseUnit Unit, SkillCastTarget Descriptor)> Hits = [];
        public override void Apply(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
            SkillCastTarget targetObj, CastAction castObj, EffectSource source, SkillObject skillObject,
            DateTime time, CompressedGamePackets packetBuilder = null) => Hits.Add((target, targetObj));
    }

    private sealed class CaptureSkillHit : DoodadFuncSkillHit
    {
        public override bool CompletesFromClientPacket => true;
        public override void Use(BaseUnit caster, Doodad owner, uint skillId, int nextPhase = 0)
        {
            if (AdvancesPhase(SkillId, skillId)) owner.Data++;
            owner.ToNextPhase = false;
        }
    }

    private sealed class TestCaster : Unit { public override float ModelSize => 0; }

    [Test]
    public async Task SkyfinPulse_NotifiesNearbySkillHitObjectsBeforeEffectTargetLimit()
    {
        var manager = Manager.GetValue(null);
        typeof(DoodadManager).GetField("_funcsByGroups", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<uint, List<DoodadFunc>>
            {
                [44090] = [new() { GroupId = 44090, FuncId = 5555, FuncType = "DoodadFuncSkillHit" }]
            });
        typeof(DoodadManager).GetField("_funcTemplates", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<string, Dictionary<uint, DoodadFuncTemplate>>
            {
                ["DoodadFuncSkillHit"] = new() { [5555] = new CaptureSkillHit { SkillId = 43798 } }
            });
        var skyfin = new TestCaster { ObjId = 699, Level = 50 };
        var near = new Doodad { ObjId = 700, TemplateId = 14916, FuncGroupId = 44090 };
        var near2 = new Doodad { ObjId = 701, TemplateId = 14916, FuncGroupId = 44090 };
        var far = new Doodad { ObjId = 702, TemplateId = 14916, FuncGroupId = 44090 };
        skyfin.Transform.Local.SetPosition(32, 32, 0, 0, 0, 0);
        near.Transform.Local.SetPosition(37, 32, 0, 0, 0, 0);
        near2.Transform.Local.SetPosition(51, 32, 0, 0, 0, 0);
        far.Transform.Local.SetPosition(53, 32, 0, 0, 0, 0);
        var region = new Region(null, 0, 0, 378);
        typeof(Region).GetField("_objects", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(region, new GameObject[] { skyfin, near, near2, far });
        typeof(Region).GetField("_objectsSize", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(region, 4);
        typeof(Region).GetField("_neighbors", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(region, new[] { region });
        skyfin.Region = region;
        var capture = new CaptureEffect();
        var template = new SkillTemplate { Id = 43798, TargetAreaRadius = 20, TargetAreaCount = 1,
            TargetType = SkillTargetType.Self, TargetSelection = SkillTargetSelection.Source,
            TargetRelation = SkillTargetRelation.Any };
        // A probe effect also verifies that ordinary effect targets stay capped at one.
        template.Effects.Add(new SkillEffect { Template = capture, ApplicationMethod = SkillEffectApplicationMethod.Target,
            StartLevel = 1, EndLevel = 99, Friendly = true, NonFriendly = true, Front = true, Back = true, Chance = 100 });
        new Skill(template).ApplyEffects(skyfin, new SkillCasterUnit(skyfin.ObjId), skyfin,
            new SkillCastUnitTarget { ObjId = skyfin.ObjId }, new SkillObject());
        await Assert.That(near.Data).IsEqualTo(1);
        await Assert.That(near2.Data).IsEqualTo(1);
        await Assert.That(far.Data).IsEqualTo(0);
        await Assert.That(capture.Hits.Count).IsEqualTo(1);
        await Assert.That(capture.Hits[0].Unit).IsEqualTo(skyfin);
    }

    [Test]
    public async Task WorkbenchAreaCastAppliesToSelectedBankExactlyOnce()
    {
        var bank = new Doodad { ObjId = 101320, TemplateId = 13571, FuncGroupId = 39797 };
        var hits = Apply(bank, SkillTargetSelection.Target, SkillTargetType.Doodad, 20);
        await Assert.That(hits.Count).IsEqualTo(1);
        await Assert.That(ReferenceEquals(hits[0].Unit, bank)).IsTrue();
        await Assert.That(hits[0].Descriptor is SkillCastDoodadTarget).IsTrue();
        await Assert.That(hits[0].Descriptor.ObjId).IsEqualTo(bank.ObjId);
    }

    [Test]
    public async Task OrdinarySingleTargetAndSourceCenteredDoodadCastsRemainSingle()
    {
        var bank = new Doodad { ObjId = 101320 };
        await Assert.That(Apply(bank, SkillTargetSelection.Target, SkillTargetType.Doodad, 0).Count).IsEqualTo(1);
        await Assert.That(Apply(bank, SkillTargetSelection.Source, SkillTargetType.Doodad, 20).Count).IsEqualTo(1);
    }

    [Test]
    public async Task LocationSelectionAndOtherTargetTypesDoNotGainAnExtraCenter()
    {
        var bank = new Doodad { ObjId = 101320 };
        await Assert.That(Apply(bank, SkillTargetSelection.Location, SkillTargetType.Doodad, 20).Count).IsEqualTo(0);
        await Assert.That(Apply(bank, SkillTargetSelection.Target, SkillTargetType.Pos, 20).Count).IsEqualTo(0);
        await Assert.That(Apply(new Unit { ObjId = 50 }, SkillTargetSelection.Target, SkillTargetType.AnyUnit, 20).Count).IsEqualTo(0);
    }

    [Test]
    public async Task SourceOnceEffectStillAppliesToCasterInsteadOfDoodad()
    {
        var bank = new Doodad { ObjId = 101320 };
        var hits = Apply(bank, SkillTargetSelection.Target, SkillTargetType.Doodad, 20, SkillEffectApplicationMethod.SourceOnce);
        await Assert.That(hits.Count).IsEqualTo(1);
        await Assert.That(hits[0].Unit.ObjId).IsEqualTo(699u);
    }

    private static List<(BaseUnit Unit, SkillCastTarget Descriptor)> Apply(BaseUnit bank,
        SkillTargetSelection selection, SkillTargetType type, int radius,
        SkillEffectApplicationMethod method = SkillEffectApplicationMethod.Target)
    {
        var capture = new CaptureEffect();
        var template = new SkillTemplate { Id = 40467, TargetAreaRadius = radius,
            TargetType = type, TargetSelection = selection, TargetRelation = SkillTargetRelation.Any };
        template.Effects.Add(new SkillEffect { Template = capture, ApplicationMethod = method,
            StartLevel = 1, EndLevel = 99, Friendly = true, NonFriendly = true, Front = true, Back = true, Chance = 100 });
        var caster = new Unit { ObjId = 699, Level = 55 };
        // No neighbors: the region lookup returns empty, reproducing the missing center defect.
        new Skill(template).ApplyEffects(caster, new SkillCasterUnit(caster.ObjId), bank,
            new SkillCastDoodadTarget { ObjId = bank.ObjId }, new SkillObject());
        return capture.Hits;
    }
}
