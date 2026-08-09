using System;
using System.Collections.Generic;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class EnchantScaleRatio
    {
        public ushort Id { get; set; }
        public int BreakRatio { get; set; }
        public int Cost { get; set; }
        public uint CurrencyId { get; set; }
        public int DisableRatio { get; set; }
        public int DownMax { get; set; }
        public int DownRatio { get; set; }
        public int GreatSuccessRatio { get; set; }
        public string Name { get; set; } = string.Empty;
        public int Scale { get; set; }
        public int SuccessRatio { get; set; }

        public double Multiplier => 1d + Scale / 1000d;
    }

    public enum TemperTargetKind
    {
        Weapon = 1,
        Armor = 2
    }

    // x2ui/chat/center_message_manager.lua and x2game FUN_39302650.
    public enum ItemRefurbishmentResult
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
        public int SuccessThreshold { get; set; }
        public int BreakThreshold { get; set; }
        public int DisableThreshold { get; set; }
        public int DowngradeThreshold { get; set; }
        public int FailRatio { get; set; }
        public int GreatSuccessRatio { get; set; }

        public int SuccessRatio => SuccessThreshold;
        public int BreakRatio => BreakThreshold - SuccessThreshold;
        public int DisableRatio => DisableThreshold - BreakThreshold;
        public int DowngradeRatio => DowngradeThreshold - DisableThreshold;
    }

    public sealed class TemperAttempt
    {
        public Item Item { get; set; }
        public TemperTargetKind TargetKind { get; set; }
        public ushort BeforeScaleId { get; set; }
        public ushort SuccessScaleId { get; set; }
        public ushort GreatSuccessScaleId { get; set; }
        public EnchantScaleRatio Ratio { get; set; }
        public ItemGradeEnchantingSupportDefinition Support { get; set; }
        public TemperProbabilityProfile Probabilities { get; set; }
        public bool GreatSuccessEnabled { get; set; }
    }

    public sealed class TemperOutcome
    {
        public ItemRefurbishmentResult Result { get; set; }
        public ushort AfterScaleId { get; set; }
    }

    public interface IItemEnchantScaleService
    {
        bool NativeCatalogueAvailable { get; }
        bool NativeMutationEnabled { get; }
        void Clear();
        void MarkNativeCatalogueAvailable();
        void Register(EnchantScaleRatio ratio);
        void RegisterForbiddenItem(uint itemId);
        void RegisterSupport(ItemGradeEnchantingSupportDefinition support);
        EnchantScaleRatio Get(ushort id);
        ItemGradeEnchantingSupportDefinition GetSupport(uint itemId);
        double GetMultiplier(ushort id);
        bool CanTemper(Item item);
        bool TryGetTargetKind(Item item, out TemperTargetKind targetKind);
        bool TryCreateAttempt(Item item, int nativeTargetKind, bool greatSuccessEnabled,
            uint supportItemId, out TemperAttempt attempt, out string failure);
        TemperOutcome ResolveOutcome(TemperAttempt attempt, int outcomeRoll, int downgradeRoll);
    }

    /// <summary>
    /// AA8 temper authority. ScaledA stores the enchant-scale ratio id sent in
    /// the equipment detail; legacy TemperPhysical/TemperMagical are not used.
    /// Probability normalization mirrors x2game FUN_39a4e4c0/FUN_39a4b830.
    /// </summary>
    public sealed class ItemEnchantScaleService : IItemEnchantScaleService
    {
        public const ushort NativeUnrestrictedScaleId = 31;
        public const int ProbabilityBase = 10000;

        private readonly Dictionary<ushort, EnchantScaleRatio> _ratios = new();
        private readonly Dictionary<uint, ItemGradeEnchantingSupportDefinition> _supports = new();
        private readonly HashSet<uint> _forbiddenItems = new();

        public static ItemEnchantScaleService Instance { get; } = new();

        public bool NativeCatalogueAvailable { get; private set; }

        public bool NativeMutationEnabled =>
            NativeCatalogueAvailable &&
            _ratios.Count == 31 &&
            _ratios.ContainsKey(1) &&
            _ratios.ContainsKey(30) &&
            _ratios.ContainsKey(NativeUnrestrictedScaleId);

        public void Clear()
        {
            NativeCatalogueAvailable = false;
            _ratios.Clear();
            _supports.Clear();
            _forbiddenItems.Clear();
        }

        public void MarkNativeCatalogueAvailable()
        {
            NativeCatalogueAvailable = true;
        }

        public void Register(EnchantScaleRatio ratio)
        {
            if (ratio != null)
                _ratios[ratio.Id] = ratio;
        }

        public void RegisterForbiddenItem(uint itemId)
        {
            _forbiddenItems.Add(itemId);
        }

        public void RegisterSupport(ItemGradeEnchantingSupportDefinition support)
        {
            if (support != null)
                _supports[support.ItemId] = support;
        }

        public EnchantScaleRatio Get(ushort id)
        {
            return _ratios.TryGetValue(id, out var ratio) ? ratio : null;
        }

        public ItemGradeEnchantingSupportDefinition GetSupport(uint itemId)
        {
            return _supports.TryGetValue(itemId, out var support) ? support : null;
        }

        public double GetMultiplier(ushort id)
        {
            return NativeCatalogueAvailable && _ratios.TryGetValue(id, out var ratio)
                ? ratio.Multiplier
                : 1d;
        }

        public bool CanTemper(Item item)
        {
            return NativeCatalogueAvailable &&
                   item is EquipItem &&
                   item.Template?.MaxEnchantScaleId > 0 &&
                   !_forbiddenItems.Contains(item.TemplateId);
        }

        public bool TryGetTargetKind(Item item, out TemperTargetKind targetKind)
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

        public bool TryCreateAttempt(
            Item item,
            int nativeTargetKind,
            bool greatSuccessEnabled,
            uint supportItemId,
            out TemperAttempt attempt,
            out string failure)
        {
            attempt = null;
            failure = string.Empty;
            if (!NativeMutationEnabled)
            {
                failure = "The complete AA8 enchant-scale catalogue is not active.";
                return false;
            }

            if (!CanTemper(item) || !TryGetTargetKind(item, out var targetKind))
            {
                failure = "The target has no complete AA8 temper definition.";
                return false;
            }

            if ((int)targetKind != nativeTargetKind)
            {
                failure =
                    $"Catalyst target kind {nativeTargetKind} does not match {targetKind}.";
                return false;
            }

            // Native AA8 instances use a real scale descriptor. Id 31 is the
            // global sentinel and id 30 is the highest playable scale.
            var beforeScaleId = item.ScaledA;
            if (beforeScaleId == 0)
            {
                failure = "The item has no initialized AA8 enchant-scale descriptor.";
                return false;
            }

            var maxScaleId = (ushort)item.Template.MaxEnchantScaleId;
            if (beforeScaleId >= maxScaleId)
            {
                failure = "The item is already at its AA8 temper cap.";
                return false;
            }

            if (!_ratios.TryGetValue(beforeScaleId, out var ratio))
            {
                failure = $"Missing native ratio {beforeScaleId}.";
                return false;
            }

            var successScaleId = StepScale(beforeScaleId, 1, maxScaleId);
            var greatScaleId = StepScale(beforeScaleId, 2, maxScaleId);
            if (successScaleId == beforeScaleId)
            {
                failure = "No native successor scale exists.";
                return false;
            }

            ItemGradeEnchantingSupportDefinition support = null;
            if (supportItemId != 0)
            {
                support = GetSupport(supportItemId);
                if (support == null)
                {
                    failure = $"Support item {supportItemId} is not in the AA8 support catalogue.";
                    return false;
                }

                var kindBit = 1 << ((int)targetKind & 31);
                if ((support.ImplementationFlags & kindBit) == 0)
                {
                    failure =
                        $"Support item {supportItemId} does not support {targetKind}.";
                    return false;
                }

                var unrestricted =
                    support.RequiredScaleMinId == NativeUnrestrictedScaleId &&
                    support.RequiredScaleMaxId == NativeUnrestrictedScaleId;
                if (!unrestricted &&
                    (beforeScaleId < support.RequiredScaleMinId ||
                     beforeScaleId > support.RequiredScaleMaxId))
                {
                    failure =
                        $"Support item {supportItemId} does not support scale {beforeScaleId}.";
                    return false;
                }
            }

            attempt = new TemperAttempt
            {
                Item = item,
                TargetKind = targetKind,
                BeforeScaleId = beforeScaleId,
                SuccessScaleId = successScaleId,
                GreatSuccessScaleId = greatScaleId,
                Ratio = ratio,
                Support = support,
                GreatSuccessEnabled = greatSuccessEnabled,
                Probabilities = NormalizeProbabilities(ratio, support, greatSuccessEnabled)
            };
            return true;
        }

        public TemperOutcome ResolveOutcome(
            TemperAttempt attempt,
            int outcomeRoll,
            int downgradeRoll)
        {
            if (attempt == null)
                throw new ArgumentNullException(nameof(attempt));
            ValidateRoll(outcomeRoll, nameof(outcomeRoll));

            var probabilities = attempt.Probabilities;
            if (outcomeRoll < probabilities.SuccessThreshold)
            {
                if (attempt.GreatSuccessEnabled &&
                    outcomeRoll < probabilities.GreatSuccessRatio)
                {
                    return new TemperOutcome
                    {
                        Result = ItemRefurbishmentResult.GreatSuccess,
                        AfterScaleId = attempt.GreatSuccessScaleId
                    };
                }

                return new TemperOutcome
                {
                    Result = ItemRefurbishmentResult.Success,
                    AfterScaleId = attempt.SuccessScaleId
                };
            }

            if (outcomeRoll < probabilities.BreakThreshold)
                return Result(ItemRefurbishmentResult.Break, attempt.BeforeScaleId);
            if (outcomeRoll < probabilities.DisableThreshold)
                return Result(ItemRefurbishmentResult.Disable, attempt.BeforeScaleId);
            if (outcomeRoll < probabilities.DowngradeThreshold)
            {
                var downMax = Math.Max(1, attempt.Ratio.DownMax);
                if (downgradeRoll < 1 || downgradeRoll > downMax)
                    throw new ArgumentOutOfRangeException(nameof(downgradeRoll));
                return Result(
                    ItemRefurbishmentResult.Downgrade,
                    StepScale(attempt.BeforeScaleId, -downgradeRoll, 30));
            }

            return Result(ItemRefurbishmentResult.Fail, attempt.BeforeScaleId);
        }

        public static TemperProbabilityProfile NormalizeProbabilities(
            EnchantScaleRatio ratio,
            ItemGradeEnchantingSupportDefinition support,
            bool greatSuccessEnabled)
        {
            if (ratio == null)
                throw new ArgumentNullException(nameof(ratio));

            var breakRaw = ratio.BreakRatio;
            var downgradeRaw = ratio.DownRatio;
            var disableRaw = ratio.DisableRatio;
            var success = ratio.SuccessRatio;
            var greatRaw = greatSuccessEnabled ? ratio.GreatSuccessRatio : 0;

            if (support != null)
            {
                breakRaw = ApplySupport(
                    breakRaw, support.AddBreakRatio, support.AddBreakMultiplier);
                disableRaw = ApplySupport(
                    disableRaw, support.AddDisableRatio, support.AddDisableMultiplier);
                downgradeRaw = ApplySupport(
                    downgradeRaw, support.AddDowngradeRatio,
                    support.AddDowngradeMultiplier);
                success = ApplySupport(
                    success, support.AddSuccessRatio, support.AddSuccessMultiplier);
                greatRaw = greatSuccessEnabled
                    ? ApplySupport(
                        greatRaw, support.AddGreatSuccessRatio,
                        support.AddGreatSuccessMultiplier)
                    : 0;
            }

            // FUN_39a4b830: great is conditional on success; destructive and
            // downgrade ratios are conditional on failure.
            var greatAbsolute = (int)(greatRaw * 0.0001f * success);
            var failure = ProbabilityBase - success;
            var breakAbsolute = (int)(breakRaw * 0.0001f * failure);
            var disableAbsolute = (int)(disableRaw * 0.0001f * failure);
            var downgradeAbsolute = (int)(downgradeRaw * 0.0001f * failure);
            var failAbsolute = Clamp(
                failure - breakAbsolute - disableAbsolute - downgradeAbsolute);
            var breakThreshold = Math.Min(ProbabilityBase, success + breakAbsolute);
            var disableThreshold =
                Math.Min(ProbabilityBase, breakThreshold + disableAbsolute);
            var downgradeThreshold =
                Math.Min(ProbabilityBase, disableThreshold + downgradeAbsolute);

            return new TemperProbabilityProfile
            {
                SuccessThreshold = Clamp(success),
                BreakThreshold = breakThreshold,
                DisableThreshold = disableThreshold,
                DowngradeThreshold = downgradeThreshold,
                FailRatio = failAbsolute,
                GreatSuccessRatio = Clamp(greatAbsolute)
            };
        }

        private ushort StepScale(ushort currentId, int count, ushort maximumId)
        {
            var current = currentId;
            var direction = Math.Sign(count);
            for (var step = 0; step < Math.Abs(count); step++)
            {
                var candidate = current + direction;
                if (candidate < 1 || candidate > maximumId ||
                    !_ratios.ContainsKey((ushort)candidate))
                    break;
                current = (ushort)candidate;
            }
            return current;
        }

        private static int ApplySupport(int value, int add, int multiplier)
        {
            // Native code performs the expression in float and truncates.
            return Clamp((int)((multiplier * 0.0001f + 1f) * (add + value)));
        }

        private static int Clamp(int value)
        {
            return Math.Max(0, Math.Min(ProbabilityBase, value));
        }

        private static void ValidateRoll(int roll, string name)
        {
            if (roll < 0 || roll >= ProbabilityBase)
                throw new ArgumentOutOfRangeException(name);
        }

        private static TemperOutcome Result(
            ItemRefurbishmentResult result,
            ushort afterScaleId)
        {
            return new TemperOutcome
            {
                Result = result,
                AfterScaleId = afterScaleId
            };
        }
    }
}
