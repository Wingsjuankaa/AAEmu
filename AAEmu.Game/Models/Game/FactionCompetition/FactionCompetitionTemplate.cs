namespace AAEmu.Game.Models.Game.FactionCompetition;

public enum FactionCompetitionResetKind : byte
{
    All = 1,
    WinnerOnly = 2,
    AllIgnoreRequiredPoint = 3
}
public enum FactionCompetitionMode : byte
{
    Pvp = 0,
    Pve = 1
}

/// <summary>Authoritative projection of faction_competitions plus its zone binding.</summary>
public sealed class FactionCompetitionTemplate
{
    public uint Id { get; init; }
    public ushort ZoneGroupId { get; init; }
    public FactionCompetitionMode Mode { get; init; }
    public int PcKillPoint { get; init; }
    public int NpcKillPoint { get; init; }
    public int QuestCompletePoint { get; init; }
    public uint RequiredPoint { get; init; }
    public FactionCompetitionResetKind ResetKind { get; init; }
    public bool ForceChangeState { get; init; }
    public uint ForceStopTowerDefId { get; init; }
    public byte ZoneStateKind { get; init; }
}
