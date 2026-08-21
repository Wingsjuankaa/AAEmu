namespace AAEmu.Game.Models.Game.Attendance;

/// <summary>One retail reward row for an account-attendance campaign.</summary>
public sealed record AccountAttendanceReward(
    uint Id,
    int Year,
    int Month,
    int DayCount,
    uint ItemId,
    int ItemGradeId,
    int ItemCount,
    bool AdditionalReward);
