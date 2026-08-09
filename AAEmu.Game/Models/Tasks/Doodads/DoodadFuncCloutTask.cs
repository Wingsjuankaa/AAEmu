using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Tasks.Doodads
{
    /// <summary>
    /// Completes a native doodad clout on the game scheduler.
    /// </summary>
    public class DoodadFuncCloutTask : DoodadFuncTask
    {
        private readonly Unit _caster;
        private readonly Doodad _owner;
        private readonly int _nextPhase;
        private readonly AreaTrigger _areaTrigger;

        public DoodadFuncCloutTask(
            Unit caster,
            Doodad owner,
            int nextPhase,
            AreaTrigger areaTrigger)
            : base(caster, owner, 0)
        {
            _caster = caster;
            _owner = owner;
            _nextPhase = nextPhase;
            _areaTrigger = areaTrigger;
        }

        public override void Execute()
        {
            // Close gameplay state before retiring its visual owner. AA8 phase
            // prefabs can contain continuous emitters which only stop when their
            // doodad leaves both the region and the world registry.
            AreaTriggerManager.Instance.RemoveAreaTrigger(_areaTrigger);

            if (_owner.FuncTask == this)
                _owner.FuncTask = null;

            if (_nextPhase == -1)
            {
                _owner.Delete();
                return;
            }

            _owner.DoPhaseFuncs(_caster, _nextPhase);
        }
    }
}
