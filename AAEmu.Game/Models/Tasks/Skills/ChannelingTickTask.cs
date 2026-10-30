using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.Game.Models.Tasks.Skills;

/// <summary>
/// Drains <c>skills.channeling_mana</c> once per <c>channeling_tick</c> of a running channel.
/// </summary>
/// <remarks>
/// Scheduled by <see cref="Skill.StartChanneling"/> for the ten skills that charge per tick and cancelled
/// by <see cref="Skill.EndChanneling"/>, so a channel stopped early cannot keep draining after its
/// SCSkillEnded. The task stops itself when the channel's caster no longer owes anything, which covers a
/// channel whose caster ran out of mana or died in the meantime.
/// </remarks>
public class ChannelingTickTask(Skill skill, BaseUnit caster) : SkillTask(skill)
{
    private readonly MechanicsSandboxExecution.Stamp _sandboxExecution = skill.SandboxExecutionStamp;
    public override void Execute()
    {
        using var execution = MechanicsSandboxExecution.EnterScheduled(caster, _sandboxExecution);
        if (!execution.Allowed)
            return;
        if (Skill.Cancelled || caster is not Unit unit || unit.IsDead)
            return;

        var cost = ChannelingRules.ManaPerTick(Skill.Template.ChannelingMana, unit.Mp);
        if (cost <= 0)
            return;

        unit.ReduceCurrentMp(null, cost);
    }
}
