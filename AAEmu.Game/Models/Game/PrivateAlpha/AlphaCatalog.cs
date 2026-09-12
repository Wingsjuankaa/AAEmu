using System.Text.Json;
using AAEmu.Game.Core.Managers;

namespace AAEmu.Game.Models.Game.PrivateAlpha;

public static class AlphaCatalog
{
    private static readonly Lazy<(uint Id, string Search)[]> Index = new(() =>
    {
        // Produced from the exact Spanish client by PatchAa10PrivateAlpha.py.
        var path = Path.Combine(AAEmu.Commons.IO.FileManager.AppPath, "Data", "private_alpha_catalog.json");
        var names = JsonSerializer.Deserialize<Dictionary<uint, string>>(File.ReadAllText(path));
        return ItemManager.Instance.GetAllItems()
            .Where(item => item.Id != AlphaRules.KeyTemplateId && names.ContainsKey(item.Id))
            .Select(item => (item.Id, AlphaRules.Normalize(names[item.Id] + " " + (item.searchString ?? item.Name))))
            .OrderBy(item => item.Id).ToArray();
    });

    public static uint[] Search(string query)
    {
        var normalized = AlphaRules.Normalize(query.Trim());
        var numeric = uint.TryParse(normalized, out var exactId);
        return Index.Value.Where(item => normalized.Length == 0 ||
            (numeric ? item.Id == exactId : item.Search.Contains(normalized, StringComparison.Ordinal)))
            .Select(item => item.Id).ToArray();
    }
}
