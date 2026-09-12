using System.Globalization;
using System.Text;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.PrivateAlpha;

public static class AlphaRules
{
    public const uint KeyTemplateId = 900001;
    public const int PageSize = 10;
    public const int MaxPointsPerRequest = 100000;
    public static ItemTemplate CreateKey() => new()
    {
        Id = KeyTemplateId, Name = "Llave de alpha privada", CategoryId = 64,
        Level = 1, LevelRequirement = 1, BindType = ItemBindType.BindOnPickup,
        MaxCount = 1, FixedGrade = 0, Sellable = false,
        searchString = "llave de alpha privada"
    };

    public static string Normalize(string text)
    {
        var chars = (text ?? "").Normalize(NormalizationForm.FormD)
            .Where(c => CharUnicodeInfo.GetUnicodeCategory(c) != UnicodeCategory.NonSpacingMark)
            // Docker runs with invariant globalization: FormD is a no-op there.
            // Fold Spanish precomposed letters explicitly as well as combining marks.
            .Select(c => c switch
            {
                'á' or 'Á' => 'a', 'é' or 'É' => 'e', 'í' or 'Í' => 'i',
                'ó' or 'Ó' => 'o', 'ú' or 'Ú' or 'ü' or 'Ü' => 'u',
                'ñ' or 'Ñ' => 'n', _ => c
            }).ToArray();
        return new string(chars).ToLowerInvariant().Normalize(NormalizationForm.FormC);
    }

    public static bool CanUse(bool enabled, bool granted) => enabled && granted;
    public static bool TryPoints(int current, int amount, out int total)
    {
        total = current;
        if (current < 0 || !ValidAmount(amount, MaxPointsPerRequest) || current > int.MaxValue - amount) return false;
        total += amount;
        return true;
    }
    public static bool ValidAmount(int amount, int maximum) => amount > 0 && amount <= maximum;
    public static int StacksNeeded(int count, int stackSize) =>
        count <= 0 || stackSize <= 0 ? int.MaxValue : (int)(((long)count + stackSize - 1) / stackSize);
    public static bool TryGold(long current, int gold, int max, out long total)
    {
        total = current;
        if (current < 0 || !ValidAmount(gold, max) || current > long.MaxValue - (long)gold * 10000) return false;
        total += (long)gold * 10000; return true;
    }
}
