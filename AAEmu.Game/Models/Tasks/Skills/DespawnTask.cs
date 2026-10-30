using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.MechanicsSandbox;

namespace AAEmu.Game.Models.Tasks.Skills;

public class DespawnTask(BaseUnit caster) : Task
{
    private readonly MechanicsSandboxExecution.Stamp _sandboxExecution = MechanicsSandboxExecution.Capture(caster);
    public override void Execute()
    {
        using var execution = MechanicsSandboxExecution.EnterScheduled(caster, _sandboxExecution);
        if (!execution.Allowed)
            return;
        if (caster is not Npc npc)
            return;

        ObjectIdManager.Instance.ReleaseId(npc.ObjId);
        npc.Delete();
    }
}
