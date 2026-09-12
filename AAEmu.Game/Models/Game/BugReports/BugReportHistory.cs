using System.Globalization;
using System.Text;
using AAEmu.Commons.Utils.DB;
using MySql.Data.MySqlClient;

namespace AAEmu.Game.Models.Game.BugReports;

public sealed record BugReportSummary(long Id, DateTime CreatedAt, string Status, string Category,
    uint EntityId, string EntityName, string Detail);

public static class BugReportHistory
{
    public const int PageSize = 4;
    // Every read binds BOTH trusted session owners, including direct detail reads.
    public static MySqlCommand OwnedCommand(MySqlConnection connection, uint account, uint character)
    {
        var command = connection.CreateCommand();
        command.Parameters.AddWithValue("@account", account);
        command.Parameters.AddWithValue("@character", character);
        return command;
    }
    public const string OwnerFilter = "account_id=@account AND character_id=@character";
    private const string Fields = "id,created_at,status,category,entity_id,entity_name,detail";
    private static BugReportSummary Read(MySqlDataReader r) => new(r.GetInt64(0), r.GetDateTime(1),
        r.GetString(2), r.GetString(3), r.GetUInt32(4), r.GetString(5), r.GetString(6));

    public static (int Page, int Pages, int Total, List<BugReportSummary> Rows) List(uint account, uint character, int page)
    {
        using var db = MySQL.CreateConnection();
        using var cmd = OwnedCommand(db, account, character);
        cmd.CommandText = $"SELECT COUNT(*) FROM bug_reports WHERE {OwnerFilter}";
        var total = Convert.ToInt32(cmd.ExecuteScalar());
        var pages = Math.Max(1, (total + PageSize - 1) / PageSize);
        page = Math.Clamp(page, 0, pages - 1);
        cmd.CommandText = $"SELECT {Fields} FROM bug_reports WHERE {OwnerFilter} ORDER BY created_at DESC,id DESC LIMIT @offset,@limit";
        cmd.Parameters.AddWithValue("@offset", page * PageSize); cmd.Parameters.AddWithValue("@limit", PageSize);
        using var reader = cmd.ExecuteReader();
        List<BugReportSummary> rows = [];
        while (reader.Read()) rows.Add(Read(reader));
        return (page, pages, total, rows);
    }

    public static BugReportSummary Find(uint account, uint character, long id)
    {
        using var db = MySQL.CreateConnection();
        using var cmd = OwnedCommand(db, account, character);
        cmd.CommandText = $"SELECT {Fields} FROM bug_reports WHERE {OwnerFilter} AND id=@id";
        cmd.Parameters.AddWithValue("@id", id);
        using var reader = cmd.ExecuteReader();
        return reader.Read() ? Read(reader) : null;
    }

    public static string Hex(string text, int runes) => Convert.ToHexString(Encoding.UTF8.GetBytes(string.Concat(text.EnumerateRunes().Take(runes))));
    public static string Summary(BugReportSummary r) => string.Join('/', r.Id.ToString(CultureInfo.InvariantCulture),
        r.Status, r.CreatedAt.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture), r.Category,
        r.EntityId.ToString(CultureInfo.InvariantCulture), Hex(r.EntityName, 80));

    // Small ordered frames avoid relying on the native chat widget's long-text limit.
    // No context JSON, account IDs or internal developer notes go to the player.
    public static IEnumerable<string> DetailChunks(string detail)
    {
        var bytes = Encoding.UTF8.GetBytes(detail);
        for (var i = 0; i < bytes.Length; i += 120)
            yield return Convert.ToHexString(bytes.AsSpan(i, Math.Min(120, bytes.Length - i)));
    }
}
