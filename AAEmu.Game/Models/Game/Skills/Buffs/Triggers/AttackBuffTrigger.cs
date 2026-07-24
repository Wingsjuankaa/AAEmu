using System;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Buffs.Triggers
{
    class AttackBuffTrigger : BuffTrigger
    {
        public override void Execute(object sender, EventArgs eventArgs)
        {
            var args = eventArgs as OnAttackArgs;
            _log.Trace("Buff[{0}] {1} executed. Applying {2}[{3}]!", _buff.Template.BuffId, this.GetType().Name, Template.Effect.GetType().Name, Template.Effect.Id);
            //Template.Effect.Apply()

            if (!(_owner is Unit))
            {
                _log.Warn("AttackTrigger owner is not a Unit");
                return;   
            }

            if (args?.Attacker == null || args.Target == null)
                return;
            ApplyResolved(args.Attacker, args.Target, 0);
        }

        public AttackBuffTrigger(Buff owner, BuffTriggerTemplate template) : base(owner, template)
        {

        }
    }
}
