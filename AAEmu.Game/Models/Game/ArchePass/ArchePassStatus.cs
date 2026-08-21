namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>AA10 <c>enum_arche_pass_statuses</c>; zero is the client-side invalid sentinel.</summary>
public enum ArchePassStatus : byte
{
    Invalid = 0,
    Owned = 1,
    Progress = 2,
    Expired = 3,
    Dropped = 4,
    Completed = 5
}
