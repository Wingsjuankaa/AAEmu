using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Formulas;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Models.StaticValues;
using Jace;

namespace AAEmu.UnitTests.Game.Models.Game.NPChar;

[NotInParallel]
public class NpcHeirStatsTests
{
    private static readonly FieldInfo FormulaInstance = typeof(Singleton<FormulaManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private static readonly FieldInfo SkillInstance = typeof(Singleton<SkillManager>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previousFormula;
    private object _previousSkill;

    [Before(Test)]
    public void Setup()
    {
        _previousFormula = FormulaInstance.GetValue(null);
        _previousSkill = SkillInstance.GetValue(null);
        var manager = new FormulaManager();
        FormulaInstance.SetValue(null, manager);
        SkillInstance.SetValue(null, new SkillManager(Mock.Of<IAnimationManager>().Object, Mock.Of<IPlotManager>().Object));
        _ = manager.CalculationEngine;
        // Exact r575 rows for NPC 20019: no synthetic HP or replacement quest credit.
        using var stream = typeof(NpcHeirStatsTests).Assembly.GetManifestResourceStream(
            "AAEmu.UnitTests.Fixtures.AnthalonNpcStats_r575.json")!;
        using var fixture = JsonDocument.Parse(stream);
        var formulas = new Dictionary<UnitFormulaKind, UnitFormula>();
        foreach (var row in fixture.RootElement.GetProperty("formulas").EnumerateArray())
        {
            var formula = new UnitFormula { Id = row.GetProperty("id").GetUInt32(),
                Kind = (UnitFormulaKind)row.GetProperty("kind_id").GetByte(), Owner = FormulaOwnerType.Npc,
                TextFormula = row.GetProperty("formula").GetString()! };
            if (!formula.Prepare()) throw new InvalidOperationException("Invalid native formula fixture");
            formulas.Add(formula.Kind, formula);
        }
        typeof(FormulaManager).GetField("_unitFormulas", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(manager, new Dictionary<FormulaOwnerType, Dictionary<UnitFormulaKind, UnitFormula>>
                { [FormulaOwnerType.Npc] = formulas });
        var variables = new Dictionary<uint, Dictionary<UnitFormulaVariableType, Dictionary<uint, UnitFormulaVariable>>>();
        foreach (var row in fixture.RootElement.GetProperty("variables").EnumerateArray())
        {
            var variable = new UnitFormulaVariable { FormulaId = row.GetProperty("unit_formula_id").GetUInt32(),
                Type = (UnitFormulaVariableType)row.GetProperty("variable_kind_id").GetByte(),
                Key = row.GetProperty("key").GetUInt32(), Value = row.GetProperty("value").GetSingle() };
            if (!variables.TryGetValue(variable.FormulaId, out var byType)) variables[variable.FormulaId] = byType = [];
            if (!byType.TryGetValue(variable.Type, out var byKey)) byType[variable.Type] = byKey = [];
            byKey.Add(variable.Key, variable);
        }
        typeof(FormulaManager).GetField("_unitVariables", BindingFlags.Instance | BindingFlags.NonPublic)!.SetValue(manager, variables);
    }

    [After(Test)]
    public void Cleanup()
    {
        FormulaInstance.SetValue(null, _previousFormula);
        SkillInstance.SetValue(null, _previousSkill);
    }

    private static Npc Spawn(byte heirLevel)
    {
        var manager = new NpcManager(Mock.Of<IObjectIdManager>().Object, Mock.Of<IModelManager>().Object,
            Mock.Of<IFactionManager>().Object, Mock.Of<IItemManager>().Object, Mock.Of<ITaskManager>().Object);
        var templates = (Dictionary<uint, NpcTemplate>)typeof(NpcManager)
            .GetProperty("Templates", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(manager)!;
        templates.Add(20019, new NpcTemplate { Id = 20019, Level = 55, HeirLevel = heirLevel,
            NpcTemplateId = (NpcTemplateType)9, NpcKindId = (NpcKindType)3, NpcGradeId = (NpcGradeType)3,
            FactionId = FactionsEnum.Monstrosity });
        return manager.Create(null, 1047, 20019);
    }

    [Test]
    [Arguments((byte)0, 230, 1102274, 88250)]
    [Arguments((byte)28, 342, 5555753, 130250)]
    public async Task Spawn_UsesNativeHeirLevelBeforeCalculatingPoints(byte heirLevel, int stamina, int hp, int mp)
    {
        var npc = Spawn(heirLevel);
        await Assert.That(npc.HeirLevel).IsEqualTo(heirLevel);
        await Assert.That(npc.Sta).IsEqualTo(stamina);
        await Assert.That(npc.MaxHp).IsEqualTo(hp);
        await Assert.That(npc.Hp).IsEqualTo(hp);
        await Assert.That(npc.MaxMp).IsEqualTo(mp);
        await Assert.That(npc.Mp).IsEqualTo(mp);
    }

    [Test]
    [Arguments(51, false)]
    [Arguments(50, true)]
    [Arguments(49, true)]
    [Arguments(0, false)]
    public async Task EscapeRequirement_UsesSameNativeHealthCeiling(int percent, bool allowed)
    {
        var npc = Spawn(28);
        npc.Hp = (int)(5555753L * percent / 100);
        var requirement = new UnitReqs { Id = 69579, OwnerId = 44012, OwnerType = "Skill",
            KindType = UnitReqsKindType.TargetHealthLessThan, Value1 = 1, Value2 = 50 };
        await Assert.That(requirement.Validate(npc, npc).ResultKey == SkillResultKeys.ok).IsEqualTo(allowed);
    }
}
