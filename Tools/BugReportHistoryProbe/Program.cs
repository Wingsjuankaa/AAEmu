// Read-only integration probe. Credentials are provided through stdin, never arguments/output.
using System.Text.Json;
using AAEmu.Commons.Models;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Models.Game.BugReports;

if (args.Length != 2 || !uint.TryParse(args[0], out var character) || !long.TryParse(args[1], out var id)) return 2;
MySQL.SetConfiguration(JsonSerializer.Deserialize<MySqlConnectionSettings>(Console.In.ReadToEnd())!);
using var db = MySQL.CreateConnection();
using var cmd = db.CreateCommand();
cmd.CommandText = "SELECT account_id FROM bug_reports WHERE id=@id AND character_id=@character";
cmd.Parameters.AddWithValue("@id", id); cmd.Parameters.AddWithValue("@character", character);
var account = Convert.ToUInt32(cmd.ExecuteScalar() ?? throw new InvalidOperationException("Fixture missing"));
var own = BugReportHistory.Find(account, character, id) ?? throw new InvalidOperationException("Own report missing");
if (BugReportHistory.Find(account + 1, character, id) != null || BugReportHistory.Find(account, character + 1, id) != null)
    throw new InvalidOperationException("Cross-owner detail leak");
if (BugReportHistory.List(account + 1, character, 0).Rows.Any(r => r.Id == id) ||
    BugReportHistory.List(account, character + 1, 0).Rows.Any(r => r.Id == id)) throw new InvalidOperationException("Cross-owner list leak");
var page = BugReportHistory.List(account, character, int.MaxValue);
if (page.Page != page.Pages - 1 || page.Rows.Count > 4) throw new InvalidOperationException("Pagination failed");
Console.WriteLine(JsonSerializer.Serialize(new { state = "passed", report_id = own.Id, character_id = character,
    cross_account_denied = true, cross_character_denied = true, page = page.Page, pages = page.Pages, count = page.Total,
    detail_chunk_count = BugReportHistory.DetailChunks(own.Detail).Count() }));
return 0;
