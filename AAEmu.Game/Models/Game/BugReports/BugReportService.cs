using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Chat;
using AAEmu.Game.Models.Game.NPChar;
using NLog;

namespace AAEmu.Game.Models.Game.BugReports;

public sealed class BugReportService
{
    private static readonly ConditionalWeakTable<Character, BugReportService> Sessions = new();
    private static readonly object SaveLock = new();
    private static readonly Logger Log = LogManager.GetCurrentClassLogger();
    private readonly BugReportTransport _transport = new();
    private DateTime _next;
    public static BugReportService For(Character character) => Sessions.GetValue(character, _ => new());
    private static void Reply(Character c, uint id, string kind, string text) =>
        c.SendPacket(new SCChatMessagePacket(ChatType.System, $"AA10BR1:{id:x}:{kind}:{text}"));
    public void Receive(Character c, string name, string password, bool create)
    {
        lock (_transport)
        {
            var now = DateTime.UtcNow;
            var payload = _transport.Receive(name, password, create, now, out var id);
            if (payload is null || !c.IsOnline) return;
            if (now < _next) { Reply(c, id, "error", "Espera un momento e inténtalo de nuevo."); return; }
            _next = now.AddMilliseconds(350);
            try { Execute(c, id, payload); }
            catch (Exception e)
            {
                Log.Error(e, "Bug report failed character={0} request={1}", c.Id, id);
                Reply(c, id, "error", "No se confirmó el guardado. Conservamos el texto; puedes reintentar.");
            }
        }
    }
    private static void Execute(Character c, uint id, string payload)
    {
        var f = payload.Split('/');
        if (f is ["open"]) { Reply(c, id, "open", "ready"); return; }
        if (f.Length == 2 && f[0] == "mine" && int.TryParse(f[1], out var historyPage) && historyPage is >= 0 and <= 100000)
        {
            var history = BugReportHistory.List(c.AccountId, c.Id, historyPage);
            Reply(c, id, "history", $"{history.Page}/{history.Pages}/{history.Total}");
            foreach (var row in history.Rows) Reply(c, id, "entry", BugReportHistory.Summary(row));
            Reply(c, id, "listed", history.Rows.Count.ToString());
            return;
        }
        if (f.Length == 2 && f[0] == "read" && long.TryParse(f[1], out var reportIdToRead) && reportIdToRead > 0)
        {
            var report = BugReportHistory.Find(c.AccountId, c.Id, reportIdToRead);
            if (report is null) { Reply(c, id, "error", "Reporte no disponible para este personaje."); return; }
            Reply(c, id, "report", BugReportHistory.Summary(report));
            var index = 0;
            foreach (var chunk in BugReportHistory.DetailChunks(report.Detail)) Reply(c, id, "chunk", $"{++index}/{chunk}");
            Reply(c, id, "read", index.ToString());
            return;
        }
        if (f.Length == 4 && f[0] == "search" && BugReportRules.HasEntity(f[1]) &&
            int.TryParse(f[2], out var page) && page is >= 0 and <= 100000)
        {
            var query = BugReportRules.Decode(f[3], 96);
            if (query is null) { Reply(c, id, "error", "Búsqueda demasiado larga."); return; }
            var found = BugReportCatalog.Search(f[1], query);
            var pages = Math.Max(1, (found.Length + 3) / 4); page = Math.Min(page, pages - 1);
            var rows = found.Skip(page * 4).Take(4).Select(e => $"{e.Id},{Convert.ToHexString(Encoding.UTF8.GetBytes(string.Concat(e.Name.EnumerateRunes().Take(100))))}");
            Reply(c, id, "page", $"{page}/{pages}/{found.Length}/{string.Join(';', rows)}");
            return;
        }
        if (f.Length == 5 && f[0] == "submit" && uint.TryParse(f[2], out var entityId))
        {
            var detail = BugReportRules.Decode(f[4], 2400)?.Trim();
            if (detail is null || !BugReportRules.Valid(f[1], entityId, f[3], detail))
            { Reply(c, id, "error", "Selecciona la categoría y el elemento; escribe entre 10 y 600 caracteres."); return; }
            var entity = entityId == 0 ? null : BugReportCatalog.Find(f[1], entityId);
            if (entityId != 0 && entity is null) { Reply(c, id, "error", "El elemento seleccionado no existe en el catálogo."); return; }
            var reportId = Save(c, f[1], entity, f[3], detail);
            Reply(c, id, reportId > 0 ? "saved" : "error", reportId > 0 ? reportId.ToString() : "Espera 10 segundos entre reportes. Máximo 30 por hora.");
            return;
        }
        Reply(c, id, "error", "Solicitud inválida.");
    }
    private static long Save(Character c, string category, BugReportEntity entity, string key, string detail)
    {
        lock (SaveLock)
        {
            using var db = MySQL.CreateConnection();
            using var cmd = db.CreateCommand();
            var fingerprint = BugReportRules.Fingerprint(category, entity?.Id ?? 0, detail);
            cmd.CommandText = "SELECT id,fingerprint FROM bug_reports WHERE character_id=@char AND request_key=@key";
            cmd.Parameters.AddWithValue("@char", c.Id); cmd.Parameters.AddWithValue("@key", key);
            using (var existing = cmd.ExecuteReader())
                if (existing.Read())
                {
                    if (existing.GetString(1) != fingerprint) throw new InvalidOperationException("Report key reused with different content");
                    return existing.GetInt64(0);
                }
            cmd.CommandText = "SELECT COUNT(*) FROM bug_reports WHERE account_id=@account AND created_at>UTC_TIMESTAMP()-INTERVAL 1 HOUR";
            cmd.Parameters.AddWithValue("@account", c.AccountId);
            if (Convert.ToInt32(cmd.ExecuteScalar()) >= 30) return 0;
            cmd.CommandText = "SELECT COUNT(*) FROM bug_reports WHERE account_id=@account AND created_at>UTC_TIMESTAMP()-INTERVAL 10 SECOND";
            if (Convert.ToInt32(cmd.ExecuteScalar()) > 0) return 0;
            var position = c.Transform.World.Position;
            var quest = category == "quest" ? c.Quests?.ActiveQuests.GetValueOrDefault(entity.Id) : null;
            var context = JsonSerializer.Serialize(new
            {
                schema_version = 1, client_build = "10.0.2.13-r575", feature_version = "bug-reports-v1",
                server_assembly = typeof(Character).Assembly.ManifestModule.ModuleVersionId,
                character = new { id = c.Id, name = c.Name, level = c.Level },
                location = new { zone_id = c.Transform.ZoneId, instance_id = c.Transform.InstanceId, x = position.X, y = position.Y, z = position.Z },
                target = c.CurrentTarget == null ? null : new { object_id = c.CurrentTarget.ObjId, type = c.CurrentTarget.GetType().Name, npc_template_id = (c.CurrentTarget as Npc)?.TemplateId },
                quest = quest == null ? null : new { template_id = quest.TemplateId, status = quest.Status.ToString(), step = quest.Step.ToString(), component_id = quest.CurrentComponentId },
                entity_english = entity?.English,
                player_text_is_untrusted = true
            });
            cmd.CommandText = "INSERT INTO bug_reports(created_at,updated_at,account_id,character_id,character_name,request_key,category,entity_id,entity_name,detail,fingerprint,context_json) VALUES(UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),@account,@char,@name,@key,@category,@entity,@entityName,@detail,@fingerprint,@context)";
            cmd.Parameters.AddWithValue("@name", c.Name); cmd.Parameters.AddWithValue("@category", category);
            cmd.Parameters.AddWithValue("@entity", entity?.Id ?? 0); cmd.Parameters.AddWithValue("@entityName", entity?.Name ?? "");
            cmd.Parameters.AddWithValue("@detail", detail); cmd.Parameters.AddWithValue("@fingerprint", fingerprint);
            cmd.Parameters.AddWithValue("@context", context); cmd.ExecuteNonQuery();
            Log.Info("Bug report saved id={0} character={1} category={2} entity={3}", cmd.LastInsertedId, c.Id, category, entity?.Id ?? 0);
            return cmd.LastInsertedId;
        }
    }
}
