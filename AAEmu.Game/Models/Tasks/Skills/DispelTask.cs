using System;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;

namespace AAEmu.Game.Models.Tasks.Skills
{
    public class DispelTask : Task
    {
        public WeakReference Effect;

        public DispelTask(Buff buff)
        {
            Effect = new WeakReference(buff);
        }

        public override void Execute()
        {
            if (!Effect.IsAlive)
                return;
            var eff = Effect.Target as Buff;
            if (eff == null || eff.IsEnded())
                return;
            if (eff.Owner == null)
                return;

            eff.ScheduleEffect(false);

            if (eff.IsEnded())
            {
                return;
            }

            var nextDelay = eff.Tick > 0 ? eff.Tick : eff.GetTimeLeft();
            if (nextDelay > 0)
                EffectTaskManager.Instance.AddDispelTask(eff, nextDelay);
        }
    }
}
