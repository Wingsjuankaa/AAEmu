using System.Text;
using System.Security.Cryptography;
using AAEmu.Game.Models.Game.PrivateAlpha;

namespace AAEmu.Game.Models.Game.BugReports;

public static class BugReportRules
{
    public static readonly string[] Categories = ["quest", "item", "skill", "npc", "world", "ui", "other"];
    public static bool HasEntity(string category) => category is "quest" or "item" or "skill" or "npc";
    public static bool Valid(string category, uint entity, string key, string detail) =>
        Categories.Contains(category) && (HasEntity(category) ? entity > 0 : entity == 0) &&
        key.Length is >= 8 and <= 40 && key.All(c => char.IsAsciiHexDigit(c) || c == '-') &&
        detail.Trim().Length >= 10 && detail.EnumerateRunes().Count() <= 600 &&
        Encoding.UTF8.GetByteCount(detail) <= 2400 &&
        !detail.Any(c => char.IsControl(c) && c is not ('\n' or '\r' or '\t'));
    public static string Decode(string hex, int maxBytes)
    {
        if (hex.Length > maxBytes * 2 || hex.Length % 2 != 0) return null;
        try { return new UTF8Encoding(false, true).GetString(Convert.FromHexString(hex)); }
        catch (Exception e) when (e is FormatException or DecoderFallbackException) { return null; }
    }
    public static string Fingerprint(string category, uint entity, string detail) =>
        Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes($"{category}/{entity}/{AlphaRules.Normalize(detail.Trim())}")));
}
