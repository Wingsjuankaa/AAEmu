namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Guaranteed selectable synthesis-effect replacement (AA10 special effect 187). It uses the same
/// type-9 request and 0xCE result as random reroll, but requires the group selected by the player.
/// </summary>
public sealed class ItemEvolvingSelectReRoll : ItemEvolvingReRoll
{
    protected override bool RequiresExplicitGroup => true;
}
