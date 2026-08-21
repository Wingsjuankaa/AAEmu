using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Tasks.Doodads;

public sealed class DoodadFuncCompetitionPointTask : DoodadFuncTask
{
    private readonly BaseUnit _caster;
    private readonly Doodad _owner;
    private readonly uint _sourcePhase;
    private readonly uint _point;
    private readonly int _nextPhase;

    public DoodadFuncCompetitionPointTask(
        BaseUnit caster, Doodad owner, uint sourcePhase, uint point, int nextPhase)
        : base(caster, owner, 0)
    {
        _caster = caster;
        _owner = owner;
        _sourcePhase = sourcePhase;
        _point = point;
        _nextPhase = nextPhase;
    }

    public override void Execute()
    {
        if (_owner.FuncGroupId != _sourcePhase)
        {
            TaskManager.Instance.Cancel(this);
            return;
        }

        WorldIntegration.GiveFactionCompetitionPoint?.Invoke(_caster, _point);
        if (ExecuteCount < RepeatCount)
            return;

        _owner.FuncTask = null;
        if (_nextPhase > 0)
            _owner.DoChangePhase(_caster, _nextPhase);
    }
}
