namespace AAEmu.Game.Models.Game.Housing;

/// <summary>
/// AA10 tax-panel state derived from the persisted protection deadline.
/// </summary>
public readonly record struct HousingTaxState(
    bool IsAlreadyPaid,
    sbyte WeeksWithoutPay,
    byte WeeksPrepay)
{
    public const byte MaxPrepaidWeeks = 5;
    public const byte TaxSealType = 1;
    public const byte ContributionType = 2;

    public bool CanPrepay => IsAlreadyPaid && WeeksPrepay < MaxPrepaidWeeks;

    public static HousingTaxState Evaluate(
        DateTime nowUtc,
        DateTime protectionEndUtc,
        uint daysPerTaxPeriod)
    {
        if (daysPerTaxPeriod == 0)
            return new HousingTaxState(false, 1, 0);

        var period = TimeSpan.FromDays(daysPerTaxPeriod);
        var taxDueUtc = protectionEndUtc - period;
        if (protectionEndUtc <= nowUtc)
        {
            var elapsedPeriods = (nowUtc - protectionEndUtc).Ticks / period.Ticks;
            var weeksWithoutPay = (sbyte)Math.Clamp(1 + elapsedPeriods, 1, sbyte.MaxValue);
            return new HousingTaxState(false, weeksWithoutPay, 0);
        }
        if (taxDueUtc <= nowUtc)
            return new HousingTaxState(false, 0, 0);

        // A normal weekly payment leaves the next due date less than one complete period away.
        // Every additional complete period is one AA10 prepayment, capped by MAX_PREPAID_WEEKS.
        var completePrepaidPeriods = (taxDueUtc - nowUtc).Ticks / period.Ticks;
        var weeksPrepay = (byte)Math.Clamp(completePrepaidPeriods, 0, MaxPrepaidWeeks);
        return new HousingTaxState(true, -1, weeksPrepay);
    }
}
