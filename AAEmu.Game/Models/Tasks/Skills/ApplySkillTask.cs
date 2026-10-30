using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.Game.Models.Tasks.Skills;

public class ApplySkillTask(
    Skill skill,
    BaseUnit caster,
    SkillCaster casterCaster,
    BaseUnit target,
    SkillCastTarget targetCaster,
    SkillObject skillObject)
    : Task
{
    private readonly MechanicsSandboxExecution.Stamp _sandboxExecution = skill.SandboxExecutionStamp;

    public override void Execute()
    {
        // Capture per application: an auto-attack Skill instance can be reused next attempt.
        using var sandboxExecution = MechanicsSandboxExecution.EnterScheduled(caster, _sandboxExecution);
        if (!sandboxExecution.Allowed)
            return;
        if (skill.Cancelled)
        {
            if (skill.TlId != 0)
            {
                AAEmu.Game.Core.Managers.Id.SkillTlIdManager.ReleaseId(skill.TlId);
                skill.TlId = 0;
            }
            return;
        }
        skill.ApplyEffects(caster, casterCaster, target, targetCaster, skillObject);
        skill.EndCastUnlessPlotOwnsIt(caster);
    }
}
