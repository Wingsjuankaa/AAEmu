using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services;

public sealed class EnchantScaleRatio
{
    public ushort Id { get; init; }
    public string Name { get; init; } = string.Empty;
    public int Scale { get; init; }
    public int SuccessRatio { get; init; }
    public int GreatSuccessRatio { get; init; }
    public int BreakRatio { get; init; }
    public int DisableRatio { get; init; }
    public int DownRatio { get; init; }
    public int DownMax { get; init; }
    public int Cost { get; init; }
    public uint CurrencyId { get; init; }

    public double Multiplier => 1d + Scale / 1000d;
}

public enum TemperTargetKind
{
    Weapon = 1,
    Armor = 2
}

/// <summary>Values consumed by r575's ITEM_REFURBISHMENT_RESULT event.</summary>
public enum ItemRefurbishmentResult : byte
{
    Break = 0,
    Downgrade = 1,
    Fail = 2,
    Disable = 3,
    Success = 4,
    GreatSuccess = 5
}

public sealed class TemperProbabilityProfile
{
    public int SuccessThreshold { get; init; }
    public int BreakThreshold { get; init; }
    public int DisableThreshold { get; init; }
    public int DowngradeThreshold { get; init; }
    public int FailRatio { get; init; }
    public int GreatSuccessRatio { get; init; }

    public int SuccessRatio => SuccessThreshold;
    public int BreakRatio => BreakThreshold - SuccessThreshold;
    public int DisableRatio => DisableThreshold - BreakThreshold;
    public int DowngradeRatio => DowngradeThreshold - DisableThreshold;
}

public sealed class TemperAttempt
{
    public required Item Item { get; init; }
    public TemperTargetKind TargetKind { get; init; }
    public ushort BeforeScaleId { get; init; }
    public ushort SuccessScaleId { get; init; }
    public ushort GreatSuccessScaleId { get; init; }
    public required EnchantScaleRatio Ratio { get; init; }
    public ItemGradeEnchantingSupport Support { get; init; }
    public required TemperProbabilityProfile Probabilities { get; init; }
    public bool GreatSuccessEnabled { get; init; }
}

public sealed record TemperOutcome(ItemRefurbishmentResult Result, ushort AfterScaleId);

/// <summary>
/// Native AA10 Temper catalogue and deterministic outcome resolver. Equipment detail field
/// <see cref="EquipItem.ScaledA"/> stores an <c>enchant_scale_ratios.id</c>. AA10 starts at id 0
/// (<c>none</c>) and playable equipment reaches id 30.
/// </summary>
public sealed class ItemEnchantScaleService
{
    public const ushort NativeUnrestrictedScaleId = 31;
    public const int ProbabilityBase = 10000;
    public const int NativeRatioCount = 32;

    private readonly Dictionary<ushort, EnchantScaleRatio> _ratios = [];
    private readonly Dictionary<uint, ItemGradeEnchantingSupport> _supports = [];
    private readonly HashSet<uint> _forbiddenItems = [];

    public static ItemEnchantScaleService Instance { get; } = new();

    public bool NativeCatalogueAvailable { get; private set; }
    public int RatioCount => _ratios.Count;
    public int ForbiddenItemCount => _forbiddenItems.Count;

    public bool NativeMutationEnabled =>
        NativeCatalogueAvailable &&
        _ratios.Count == NativeRatioCount &&
        _ratios.ContainsKey(0) &&
        _ratios.ContainsKey(30) &&
        _ratios.ContainsKey(NativeUnrestrictedScaleId);

    public void Clear()
    {
        NativeCatalogueAvailable = false;
        _ratios.Clear();
        _supports.Clear();
        _forbiddenItems.Clear();
    }

    public void MarkNativeCatalogueAvailable() => NativeCatalogueAvailable = true;

    public void Register(EnchantScaleRatio ratio) => _ratios[ratio.Id] = ratio;
    public void RegisterForbiddenItem(uint itemId) => _forbiddenItems.Add(itemId);
    public void RegisterSupport(ItemGradeEnchantingSupport support) => _supports[support.ItemId] = support;

    public EnchantScaleRatio Get(ushort id) => _ratios.GetValueOrDefault(id);
    public ItemGradeEnchantingSupport GetSupport(uint itemId) => _supports.GetValueOrDefault(itemId);

    public double GetMultiplier(ushort id) =>
        NativeCatalogueAvailable && _ratios.TryGetValue(id, out var ratio)
            ? ratio.Multiplier
            : 1d;

    public bool CanTemper(Item item) =>
        NativeCatalogueAvailable &&
        item is EquipItem &&
        item.Template?.MaxEnchantScaleId > 0 &&
        !_forbiddenItems.Contains(item.TemplateId);

    public static bool TryGetTargetKind(Item item, out TemperTargetKind targetKind)
    {
        switch (item)
        {
            case Weapon:
                targetKind = TemperTargetKind.Weapon;
                return true;
            case Armor:
                targetKind = TemperTargetKind.Armor;
                return true;
            default:
                targetKind = default;
                return false;
        }
    }

    public bool TryCreateAttempt(Item item, int nativeTargetKind, bool greatSuccessEnabled,
        int nativeMaximumScaleId, uint supportItemId, out TemperAttempt attempt, out string failure)
    {
        attempt = null;
        failure = string.Empty;

        if (!NativeMutationEnabled)
        {
            failure = "The complete AA10 enchant-scale catalogue is not active.";
            return false;
        }

        if (!CanTemper(item) || !TryGetTargetKind(item, out var targetKind))
        {
            failure = "The target is not temperable in the AA10 catalogue.";
            return false;
        }

        if ((int)targetKind != nativeTargetKind)
        {
            failure = $"Catalyst target kind {nativeTargetKind} does not match {targetKind}.";
            return false;
        }

        var equipment = (EquipItem)item;
        var beforeScaleId = equipment.ScaledA;
        if (nativeMaximumScaleId <= 0 || nativeMaximumScaleId > NativeUnrestrictedScaleId)
        {
            failure = $"Catalyst maximum scale {nativeMaximumScaleId} is invalid.";
            return false;
        }

        // SpecialEffect 126 value4 declares the catalyst ceiling (+30 for all four retail
        // Tempers). The item template is an independent client/server eligibility ceiling.
        var maximumScaleId = checked((ushort)Math.Min(item.Template.MaxEnchantScaleId,
            nativeMaximumScaleId));
        if (beforeScaleId >= maximumScaleId)
        {
            failure = "The item is already at its AA10 Temper cap.";
            return false;
        }

        if (!_ratios.TryGetValue(beforeScaleId, out var ratio))
        {
            failure = $"Missing AA10 enchant-scale ratio {beforeScaleId}.";
            return false;
        }

        var successScaleId = StepScale(beforeScaleId, 1, maximumScaleId);
        var greatSuccessScaleId = StepScale(beforeScaleId, 2, maximumScaleId);
        if (successScaleId == beforeScaleId)
        {
            failure = "No AA10 Temper successor scale exists.";
            return false;
        }

        ItemGradeEnchantingSupport support = null;
        if (supportItemId != 0)
        {
            support = GetSupport(supportItemId);
            if (support is null)
            {
                failure = $"Support item {supportItemId} is not in the AA10 catalogue.";
                return false;
            }

            var targetKindBit = 1 << ((int)targetKind & 31);
            if ((support.ImplementationFlags & targetKindBit) == 0)
            {
                failure = $"Support item {supportItemId} does not support {targetKind}.";
                return false;
            }

            var unrestricted = support.RequiredScaleMinId == NativeUnrestrictedScaleId &&
                               support.RequiredScaleMaxId == NativeUnrestrictedScaleId;
            if (!unrestricted &&
                (beforeScaleId < support.RequiredScaleMinId || beforeScaleId > support.RequiredScaleMaxId))
            {
                failure = $"Support item {supportItemId} does not support scale {beforeScaleId}.";
                return false;
            }
        }

        attempt = new TemperAttempt
        {
            Item = item,
            TargetKind = targetKind,
            BeforeScaleId = beforeScaleId,
            SuccessScaleId = successScaleId,
            GreatSuccessScaleId = greatSuccessScaleId,
            Ratio = ratio,
            Support = support,
            GreatSuccessEnabled = greatSuccessEnabled,
            Probabilities = NormalizeProbabilities(ratio, support, greatSuccessEnabled)
        };
        return true;
    }

    public TemperOutcome ResolveOutcome(TemperAttempt attempt, int outcomeRoll, int downgradeRoll)
    {
        ArgumentNullException.ThrowIfNull(attempt);
        if (outcomeRoll is < 0 or >= ProbabilityBase)
            throw new ArgumentOutOfRangeException(nameof(outcomeRoll));

        var probabilities = attempt.Probabilities;
        if (outcomeRoll < probabilities.SuccessThreshold)
        {
            return attempt.GreatSuccessEnabled && outcomeRoll < probabilities.GreatSuccessRatio
                ? new TemperOutcome(ItemRefurbishmentResult.GreatSuccess, attempt.GreatSuccessScaleId)
                : new TemperOutcome(ItemRefurbishmentResult.Success, attempt.SuccessScaleId);
        }

        if (outcomeRoll < probabilities.BreakThreshold)
            return new TemperOutcome(ItemRefurbishmentResult.Break, attempt.BeforeScaleId);
        if (outcomeRoll < probabilities.DisableThreshold)
            return new TemperOutcome(ItemRefurbishmentResult.Disable, attempt.BeforeScaleId);
        if (outcomeRoll < probabilities.DowngradeThreshold)
        {
            var downMax = Math.Max(1, attempt.Ratio.DownMax);
            if (downgradeRoll < 1 || downgradeRoll > downMax)
                throw new ArgumentOutOfRangeException(nameof(downgradeRoll));
            return new TemperOutcome(ItemRefurbishmentResult.Downgrade,
                StepScale(attempt.BeforeScaleId, -downgradeRoll, attempt.BeforeScaleId));
        }

        return new TemperOutcome(ItemRefurbishmentResult.Fail, attempt.BeforeScaleId);
    }

    public static TemperProbabilityProfile NormalizeProbabilities(EnchantScaleRatio ratio,
        ItemGradeEnchantingSupport support, bool greatSuccessEnabled)
    {
        ArgumentNullException.ThrowIfNull(ratio);

        var breakRaw = ratio.BreakRatio;
        var disableRaw = ratio.DisableRatio;
        var downgradeRaw = ratio.DownRatio;
        var success = ratio.SuccessRatio;
        var greatRaw = greatSuccessEnabled ? ratio.GreatSuccessRatio : 0;

        if (support is not null)
        {
            breakRaw = ApplySupport(breakRaw, support.AddBreakRatio, support.AddBreakMul);
            disableRaw = ApplySupport(disableRaw, support.AddDisableRatio, support.AddDisableMul);
            downgradeRaw = ApplySupport(downgradeRaw, support.AddDowngradeRatio, support.AddDowngradeMul);
            success = ApplySupport(success, support.AddSuccessRatio, support.AddSuccessMul);
            greatRaw = greatSuccessEnabled
                ? ApplySupport(greatRaw, support.AddGreatSuccessRatio, support.AddGreatSuccessMul)
                : 0;
        }

        success = Clamp(success);
        var greatAbsolute = Clamp((int)(greatRaw * 0.0001f * success));
        var failure = ProbabilityBase - success;
        var breakAbsolute = Clamp((int)(breakRaw * 0.0001f * failure));
        var disableAbsolute = Clamp((int)(disableRaw * 0.0001f * failure));
        var downgradeAbsolute = Clamp((int)(downgradeRaw * 0.0001f * failure));
        var breakThreshold = Math.Min(ProbabilityBase, success + breakAbsolute);
        var disableThreshold = Math.Min(ProbabilityBase, breakThreshold + disableAbsolute);
        var downgradeThreshold = Math.Min(ProbabilityBase, disableThreshold + downgradeAbsolute);

        return new TemperProbabilityProfile
        {
            SuccessThreshold = success,
            BreakThreshold = breakThreshold,
            DisableThreshold = disableThreshold,
            DowngradeThreshold = downgradeThreshold,
            FailRatio = Clamp(failure - breakAbsolute - disableAbsolute - downgradeAbsolute),
            GreatSuccessRatio = greatAbsolute
        };
    }

    private ushort StepScale(ushort currentId, int count, ushort maximumId)
    {
        var current = currentId;
        var direction = Math.Sign(count);
        for (var step = 0; step < Math.Abs(count); step++)
        {
            var candidate = current + direction;
            if (candidate < 0 || candidate > maximumId || !_ratios.ContainsKey((ushort)candidate))
                break;
            current = (ushort)candidate;
        }
        return current;
    }

    // Support additive ratios use the 10,000 probability base, but *_mul is a percentage:
    // 50 means x1.5, 100 means x2 and -100 removes the outcome. This is also stated verbatim by
    // the r575 localized charm descriptions and matches GradeEnchant.GetCharmChance.
    private static int ApplySupport(int value, int add, int multiplier) =>
        Clamp((int)((multiplier * 0.01f + 1f) * (add + value)));

    private static int Clamp(int value) => Math.Clamp(value, 0, ProbabilityBase);
}
