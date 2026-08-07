using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    /// <summary>
    /// Executes event 29 when a charged absorption buff is exhausted.
    /// </summary>
    public class AbsorptionBuffTrigger : BuffTrigger
    {
        public AbsorptionBuffTrigger(Buff buff, BuffTriggerTemplate template)
            : base(buff, template)
        {
        }

        public override void Execute(object sender, EventArgs eventArgs)
        {
            var args = eventArgs as OnAbsorptionArgs;
            var owner = _owner as Unit;
            if (owner == null)
                return;

            ApplyResolved(
                args?.Source ?? owner,
                args?.Target ?? owner,
                Template.UseDamageAmount ? args?.Amount ?? 0 : 0);
        }
    }
}
