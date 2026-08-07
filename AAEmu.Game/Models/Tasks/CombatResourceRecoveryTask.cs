using System;

using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Tasks
{
    public class CombatResourceRecoveryTask : Task
    {
        private readonly Unit _unit;

        public CombatResourceRecoveryTask(Unit unit)
        {
            _unit = unit;
        }

        public override void Execute()
        {
            if (!_unit.RegenerateCombatResources(DateTime.UtcNow))
                _unit.StopCombatResourceRecovery();
        }
    }
}
