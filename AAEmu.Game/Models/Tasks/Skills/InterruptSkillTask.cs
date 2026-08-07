using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Tasks.Skills
{
    /// <summary>
    /// Applies the delayed form of AA8 SpecialEffect DisturbCasting.
    /// Unit.InterruptSkills closes both plot execution and ordinary
    /// cast/channel tasks through their native server lifecycle.
    /// </summary>
    public sealed class InterruptSkillTask : Task
    {
        private readonly Unit _target;

        public InterruptSkillTask(Unit target)
        {
            _target = target;
        }

        public override void Execute()
        {
            _target?.InterruptSkills();
        }
    }
}
