namespace AAEmu.Game.Models.Game.Skills.Effects
{
    /// <summary>
    /// AA8 legacy high-ability resource descriptor.
    /// </summary>
    /// <remarks>
    /// AA8 stores only a minimum and maximum. The stable r575 crosswalk keeps
    /// the effect and descriptor IDs, but migrates the concrete type to
    /// CombatResourceEffect with combat_resource_id=0, chance=0 and
    /// reset_remain_time=true. Resource zero means the primary resource of the
    /// skill ability, which is Magic Source (8) for Sorcery.
    /// </remarks>
    public sealed class HighAbilityResourceEffect : CombatResourceEffect
    {
    }
}
