using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.Game.Models.Tasks.Skills;

public class UseSkillTask : Task
{
    private readonly Skill _skill;
    private readonly BaseUnit _caster;
    private readonly SkillCaster _casterCaster;
    private readonly SkillCastTarget _targetCaster;
    private readonly SkillObject _skillObject;
    private readonly MechanicsSandboxExecution.Stamp _sandboxExecution;

    public UseSkillTask(Skill skill, BaseUnit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject)
    {
        _skill = skill;
        _caster = caster;
        _sandboxExecution = MechanicsSandboxExecution.Capture(caster);
        _casterCaster = casterCaster;
        _targetCaster = targetCaster;
        _skillObject = skillObject;
    }

    public override void Execute()
    {
        using var execution = MechanicsSandboxExecution.EnterScheduled(_caster, _sandboxExecution);
        if (!execution.Allowed)
            return;
        _skill.Use(_caster, _casterCaster, _targetCaster, _skillObject, true, out _);
    }
}
