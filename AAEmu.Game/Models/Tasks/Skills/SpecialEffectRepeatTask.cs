namespace AAEmu.Game.Models.Tasks.Skills;

/// <summary>Runs subsequent pulses of a repeated special effect without blocking the packet thread.</summary>
public sealed class SpecialEffectRepeatTask(Action execute, object owner = null) : Task
{
    private readonly global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Stamp _sandboxExecution =
        global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Capture(owner);

    public override void Execute()
    {
        using var execution = global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.EnterScheduled(owner, _sandboxExecution);
        if (execution.Allowed)
            execute();
    }
}
