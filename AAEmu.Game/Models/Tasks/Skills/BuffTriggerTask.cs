namespace AAEmu.Game.Models.Tasks.Skills;

/// <summary>
/// Applies a buff trigger's effect after its authored <c>buff_triggers.delay_time</c>, without blocking the
/// thread the triggering event was raised on.
/// </summary>
public sealed class BuffTriggerTask(Action applyEffect, object owner = null) : Task
{
    private readonly global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Stamp _sandboxExecution =
        global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Capture(owner);

    public override void Execute()
    {
        using var execution = global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.EnterScheduled(owner, _sandboxExecution);
        if (execution.Allowed)
            applyEffect();
    }
}
