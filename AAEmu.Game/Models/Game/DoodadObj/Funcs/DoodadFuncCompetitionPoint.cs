using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Doodads;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

/// <summary>AA10 r575 authored periodic competition-point phase function.</summary>
public sealed class DoodadFuncCompetitionPoint : DoodadPhaseFuncTemplate
{
    public int Duration { get; init; }
    public int Tick { get; init; }
    public uint CompetitionPoint { get; init; }
    public uint ProjectileId { get; init; }
    public uint FxGroupId { get; init; }
    public int NextPhase { get; init; }

    public override bool Use(BaseUnit caster, Doodad owner)
    {
        if (caster == null || CompetitionPoint == 0)
            return false;

        var intervalMs = Math.Max(1, Tick);
        var durationMs = Math.Max(intervalMs, Duration);
        var executions = Math.Max(1, (int)Math.Ceiling((double)durationMs / intervalMs));

        if (owner.FuncTask != null)
            TaskManager.Instance.Cancel(owner.FuncTask);

        owner.FuncTask = new DoodadFuncCompetitionPointTask(
            caster, owner, owner.FuncGroupId, CompetitionPoint, NextPhase);
        TaskManager.Instance.Schedule(owner.FuncTask,
            TimeSpan.FromMilliseconds(intervalMs), TimeSpan.FromMilliseconds(intervalMs), executions);
        return false;
    }
}
