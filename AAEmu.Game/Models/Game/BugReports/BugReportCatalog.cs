using System.Text.Json;
using AAEmu.Game.Models.Game.PrivateAlpha;

namespace AAEmu.Game.Models.Game.BugReports;

public sealed record BugReportEntity(string Category, uint Id, string Name, string English);

public static class BugReportCatalog
{
    private static readonly Lazy<BugReportEntity[]> Entities = new(() =>
        JsonSerializer.Deserialize<BugReportEntity[]>(File.ReadAllText(Path.Combine(
            AAEmu.Commons.IO.FileManager.AppPath, "Data", "bug_report_catalog.json"))) ?? []);
    private static readonly Lazy<Dictionary<(string, uint), BugReportEntity>> ById = new(() =>
        Entities.Value.ToDictionary(e => (e.Category, e.Id)));
    private static readonly Lazy<(BugReportEntity Entity, string Search)[]> Index = new(() =>
        Entities.Value.Select(e => (e, AlphaRules.Normalize(e.Name + " " + e.English))).ToArray());
    public static BugReportEntity Find(string category, uint id) => ById.Value.GetValueOrDefault((category, id));
    public static BugReportEntity[] Search(string category, string query)
    {
        var q = AlphaRules.Normalize(query.Trim());
        var numeric = uint.TryParse(q, out var id);
        return Index.Value.Where(e => e.Entity.Category == category &&
            (numeric ? e.Entity.Id == id : e.Search.Contains(q, StringComparison.Ordinal)))
            .Select(e => e.Entity).OrderBy(e => e.Id).ToArray();
    }
}
