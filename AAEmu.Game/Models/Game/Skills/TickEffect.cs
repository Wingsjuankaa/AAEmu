namespace AAEmu.Game.Models.Game.Skills;

public class TickEffect
{
    public uint Id { get; set; }
    public bool OrUnitReqs { get; set; }
    public uint EffectId { get; set; }
    public uint TargetBuffTagId { get; set; }
    public uint TargetNoBuffTagId { get; set; }
}
