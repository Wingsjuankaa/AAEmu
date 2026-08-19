using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.Items;

/// <summary>One explicit item or implementation/level filter accepted by a conversion reagent pack.</summary>
public sealed class ItemConversionReagent
{
    public uint ReagentPackId { get; init; }
    public ItemImplEnum ImplId { get; init; }
    public uint InputItemId { get; init; }
    public int MinLevel { get; init; }
    public int MaxLevel { get; init; }
    public byte MinItemGrade { get; init; }
    public byte MaxItemGrade { get; init; }

    public bool IsExplicit => InputItemId != 0;

    public bool Matches(byte grade, ItemImplEnum implId, uint itemId, int level) =>
        grade >= MinItemGrade && grade <= MaxItemGrade &&
        (IsExplicit
            ? itemId == InputItemId
            : implId == ImplId && level >= MinLevel && level <= MaxLevel);
}
