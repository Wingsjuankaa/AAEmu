namespace AAEmu.Game.Models.Game.ArchePass;

/// <summary>
/// Native AA10 r575 <c>SCUpdateArchePass.reason</c> values. The client maps these values to the
/// corresponding <c>ARCHE_PASS_*</c> UI events.
/// </summary>
public enum ArchePassUpdateReason : byte
{
    UpdatePoint = 1,
    UpdateRewardItem = 2,
    Dropped = 3,
    Started = 4,
    Owned = 5,
    Buy = 6,
    UpgradePremium = 7,
    Expired = 8,
    Completed = 9,
    Reseted = 10
}
