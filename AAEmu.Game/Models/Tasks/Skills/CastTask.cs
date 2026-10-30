using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.Game.Models.Tasks.Skills;

public class CastTask(
    Skill skill,
    BaseUnit caster,
    SkillCaster casterCaster,
    BaseUnit target,
    SkillCastTarget targetCaster,
    SkillObject skillObject)
    : SkillTask(skill)
{
    private readonly MechanicsSandboxExecution.Stamp _sandboxExecution = skill.SandboxExecutionStamp;

    public override void Execute()
    {
        using var execution = MechanicsSandboxExecution.EnterScheduled(caster, _sandboxExecution);
        if (!execution.Allowed)
            return;
        if (Skill.Cancelled)
            return;

        Skill.Cast(caster, casterCaster, target, targetCaster, skillObject);
    }
}
