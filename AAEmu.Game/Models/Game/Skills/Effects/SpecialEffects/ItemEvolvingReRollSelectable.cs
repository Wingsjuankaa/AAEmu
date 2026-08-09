namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects
{
    /// <summary>
    /// AA8 SpecialEffect 187. The client uses the same evolving-reroll
    /// controller and type-9 SkillObject as SpecialEffect 136, but requires
    /// an explicit replacement modifier-group selected by the player.
    /// </summary>
    public sealed class ItemEvolvingReRollSelectable : ItemEvolvingReRoll
    {
        protected override bool RequiresExplicitGroup => true;
    }
}
