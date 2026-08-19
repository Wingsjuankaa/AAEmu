namespace AAEmu.Game.Models.Game.Char;

public sealed record BlessUthstinRoll(
    uint ItemTemplateId,
    int FunctionId,
    BlessUthstinStat IncreaseStat,
    BlessUthstinStat DecreaseStat,
    int IncreasePoints,
    int DecreasePoints,
    int PageIndex);
