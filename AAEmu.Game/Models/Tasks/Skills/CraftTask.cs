using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Tasks.Skills;

public class CraftTask(Character character, uint craftId, uint objId, long generation) : Task
{
    private readonly global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Stamp _sandboxExecution =
        global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.Capture(character);
    public override void Execute()
    {
        using var execution = global::AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxExecution.EnterScheduled(character, _sandboxExecution);
        if (!execution.Allowed)
            return;
        if (!Cancelled && character is not null)
            character.Craft.TryContinue(craftId, objId, generation);
    }
}
