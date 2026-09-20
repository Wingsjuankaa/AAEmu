using System.Runtime.CompilerServices;
using System.Text;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Chat;
using AAEmu.Game.Models.Game.PrivateAlpha;
using NLog;

namespace AAEmu.Game.Models.Game.GmPanel;

public sealed class GmPanelService
{
    public const string Prefix = "aa10gm1:";
    private static readonly ConditionalWeakTable<Character, GmPanelService> Sessions = new();
    private static readonly Logger Log = LogManager.GetCurrentClassLogger();
    private readonly AlphaTransport _transport = new();
    private DateTime _next;
    private string _confirmation;
    private uint _confirmationId, _target;
    private DateTime _expires;
    private readonly Func<Character, int> _access;
    private readonly Func<Character, bool> _online;
    private readonly Func<int, GmPanelEntry[]> _catalog;
    private readonly Func<Character, string, bool> _dispatch;
    private readonly Action<Character, uint, string, string> _reply;
    public GmPanelService() : this(c => CharacterManager.Instance.GetEffectiveAccessLevel(c), c => c.IsOnline,
        GmPanelCatalog.Get, (c, text) => CommandManager.Instance.Handle(c, text, out _), SendReply) { }

    internal GmPanelService(Func<Character, int> access, Func<Character, bool> online,
        Func<int, GmPanelEntry[]> catalog, Func<Character, string, bool> dispatch,
        Action<Character, uint, string, string> reply)
    { _access = access; _online = online; _catalog = catalog; _dispatch = dispatch; _reply = reply; }
    public static GmPanelService For(Character character) => Sessions.GetValue(character, _ => new());
    public static bool IsReserved(string name) => name.StartsWith(Prefix, StringComparison.Ordinal);
    private static string Hex(string text) => Convert.ToHexString(Encoding.UTF8.GetBytes(text));
    private static void SendReply(Character c, uint id, string kind, string value) =>
        c.SendPacket(new SCChatMessagePacket(ChatType.System, $"AA10GM1:{id:x}:{kind}:{value}"));
    private void Reply(Character c, uint id, string kind, string value) => _reply(c, id, kind, value);

    public void Receive(Character character, string name, string password, bool create) => Receive(character, name, password, create, DateTime.UtcNow);

    internal void Receive(Character character, string name, string password, bool create, DateTime now)
    {
        lock (this)
        {
            if (!IsReserved(name) || !_online(character)) return;
            var payload = _transport.Receive(AlphaTransport.Prefix + name[Prefix.Length..], password, create, now, out var id);
            if (payload is null) return;
            var access = _access(character);
            if (payload == "access") { Reply(character, id, "access", GmPanelCatalog.CanUse(access) ? "1" : "0"); return; }
            if (!GmPanelCatalog.CanUse(access))
            { _confirmation = null; Reply(character, id, "denied", "Acceso reservado al equipo GM."); return; }
            if (now < _next) { Reply(character, id, "error", "Espera un momento y vuelve a intentarlo."); return; }
            _next = now.AddMilliseconds(350);
            try { Execute(character, access, id, payload, now); }
            catch (Exception e)
            {
                Log.Error(e, "GM panel request failed character={0} request={1}", character.Id, id);
                Reply(character, id, "error", "No se completó la solicitud. Consulta el chat antes de repetirla.");
            }
        }
    }

    private void Execute(Character c, int access, uint id, string payload, DateTime now)
    {
        var catalog = _catalog(access);
        if (payload == "list")
        {
            _confirmation = null;
            foreach (var row in catalog)
                Reply(c, id, "entry", $"{row.Name}/{row.Category}/{Hex(row.Description)}/{Hex(string.Join(' ', CommandManager.Instance.GetCommandInterfaceByName(row.Name)?.CommandNames ?? []))}");
            Reply(c, id, "listed", catalog.Length.ToString()); return;
        }
        if (payload.StartsWith("detail/", StringComparison.Ordinal))
        {
            _confirmation = null;
            var row = catalog.FirstOrDefault(e => e.Name == payload[7..]);
            if (row is null) { Reply(c, id, "error", "Comando no disponible."); return; }
            Reply(c, id, "meta", $"{row.Name}/{(row.Confirm ? 1 : 0)}/{Hex(row.Example)}");
            // Split UTF-8 as hex, matching the tested report-panel framing.
            var text = Hex(row.Description + "\n\nUso y ayuda del servidor:\n" + row.Help);
            var count = (text.Length + 319) / 320;
            for (var n = 0; n < count; n++) Reply(c, id, "chunk", $"{n + 1}/{text.Substring(n * 320, Math.Min(320, text.Length - n * 320))}");
            Reply(c, id, "detail", count.ToString()); return;
        }
        string command;
        if (payload.StartsWith("confirm/", StringComparison.Ordinal))
        {
            if (_confirmation is null || payload[8..] != _confirmationId.ToString("x") || now > _expires ||
                (c.CurrentTarget?.ObjId ?? 0) != _target)
            { _confirmation = null; Reply(c, id, "error", "Confirmación vencida o cambió el objetivo. Prepara de nuevo el comando."); return; }
            command = _confirmation; _confirmation = null;
        }
        else if (payload.StartsWith("run/", StringComparison.Ordinal))
        {
            _confirmation = null;
            command = GmPanelCatalog.DecodeCommand(payload[4..]);
            if (command is null) { Reply(c, id, "error", "Comando inválido o demasiado largo (máximo 130 bytes)."); return; }
            var first = command.Split(' ')[0];
            var row = catalog.FirstOrDefault(e => e.Name == first);
            if (row is null) { Reply(c, id, "error", "Comando no disponible con tus permisos."); return; }
            if (row.Confirm)
            {
                _confirmation = command; _confirmationId = id; _expires = now.AddSeconds(20); _target = c.CurrentTarget?.ObjId ?? 0;
                Reply(c, id, "confirm", id.ToString("x")); return;
            }
        }
        else { Reply(c, id, "error", "Solicitud desconocida."); return; }
        // Recheck availability and invoke the exact dispatcher used by chat (including V2).
        if (!catalog.Any(e => e.Name == command.Split(' ')[0]))
        { Reply(c, id, "denied", "El permiso del comando ha cambiado."); return; }
        Log.Info("GM panel dispatch character={0} command={1} request={2} target={3}", c.Id, command.Split(' ')[0], id, c.CurrentTarget?.ObjId ?? 0);
        var handled = _dispatch(c, command);
        Reply(c, id, handled ? "done" : "error", handled ? "Comando enviado. Revisa el resultado en el chat." : "Comando no encontrado.");
    }
}
