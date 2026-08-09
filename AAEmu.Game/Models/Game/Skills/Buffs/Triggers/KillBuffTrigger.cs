using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    public class KillBuffTrigger : BuffTrigger
    {
        public KillBuffTrigger(Buff buff, BuffTriggerTemplate template)
            : base(buff, template)
        {
        }

        public override void Execute(object sender, EventArgs eventArgs)
        {
            if (!(eventArgs is OnKillArgs args))
                return;

            var attacker = args.Attacker ?? sender as Unit;
            if (attacker == null || args.Target == null)
                return;

            ApplyResolved(attacker, args.Target, 0);
        }
    }
}
