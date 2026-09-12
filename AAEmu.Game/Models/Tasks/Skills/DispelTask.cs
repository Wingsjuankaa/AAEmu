using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Models.Tasks.Skills;

public class DispelTask(Buff buff) : Task
{
    public WeakReference Effect = new(buff);

    public override void Execute()
    {
        if (!Effect.IsAlive)
            return;

        if (Effect.Target is not Buff eff || eff.IsEnded() || eff.Owner == null)
            return;

        // A refresh can race a task already dequeued by TaskManager. Its old
        // deadline cannot expire the new lifetime; refresh scheduled a new task.
        if (eff.Tick <= 0 && eff.Duration > 0 && eff.GetTimeLeft() > 0)
        {
            EffectTaskManager.Instance.AddDispelTask(eff, eff.GetTimeLeft());
            return;
        }

        eff.ScheduleEffect(false);

        if (eff.IsEnded())
        {
            return;
        }
        EffectTaskManager.Instance.AddDispelTask(eff, eff.Tick);
    }
}
