using System.Globalization;
using System.Runtime.CompilerServices;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Chat;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.StaticValues;
using NLog;

namespace AAEmu.Game.Models.Game.PrivateAlpha;

public sealed class AlphaService
{
    private static readonly ConditionalWeakTable<Character, AlphaService> Sessions = new();
    private static readonly Logger Log = LogManager.GetCurrentClassLogger();
    private readonly AlphaTransport _transport = new();
    private DateTime _nextRequest;
    private DateTime _nextAccessCheck;
    public static AlphaService For(Character character) => Sessions.GetValue(character, _ => new());
    public static bool IsAuthorized(uint characterId) => AlphaRules.CanUse(
        AppConfiguration.Instance.PrivateAlpha.Enabled, AlphaRepository.HasAccess(characterId));

    public static bool HasKey(Character character) => character.Inventory?.Bag?.Items
        .Any(i => i.TemplateId == AlphaRules.KeyTemplateId && i.OwnerId == character.Id && i.Count > 0) == true;

    public void Receive(Character character, string name, string password, bool create)
    {
        lock (GamePersistence.Sync)
        {
            var now = DateTime.UtcNow;
            var request = _transport.Receive(name, password, create, now, out var id);
            if (request is null || !character.IsOnline) return;
            if (request == "access")
            {
                if (now < _nextAccessCheck) return;
                _nextAccessCheck = now.AddSeconds(5);
                try { Reply(character, id, "access", IsAuthorized(character.Id) ? "1" : "0"); }
                catch (Exception exception)
                {
                    Log.Error(exception, "Private alpha access check failed character={0}", character.Id);
                    Reply(character, id, "access", "0");
                }
                return;
            }
            if (now < _nextRequest) { Reply(character, id, "error", "Espera un momento antes de solicitar otra operación."); return; }
            _nextRequest = now.AddMilliseconds(350);
            try
            {
                if (!IsAuthorized(character.Id))
                {
                    Reply(character, id, "denied", "Necesitas acceso autorizado a la alpha privada."); return;
                }
                Execute(character, id, request);
            }
            catch (Exception exception)
            {
                Log.Error(exception, "Private alpha failed character={0} request={1}", character.Id, id);
                Reply(character, id, "error", "No se completó la solicitud. Revisa el inventario antes de volver a intentar.");
            }
        }
    }

    private static void Reply(Character character, uint id, string kind, string payload) =>
        character.SendPacket(new SCChatMessagePacket(ChatType.System, $"AA10AP1:{id:x}:{kind}:{payload}"));

    private static void Execute(Character character, uint id, string request)
    {
        var fields = request.Split('/');
        if (fields is ["open"])
        {
            var config = AppConfiguration.Instance.PrivateAlpha;
            Reply(character, id, "open", $"{Math.Clamp(config.MaxGoldPerRequest, 1, 1000000)},{Math.Clamp(config.LaborCap, 1, 32767)},{Math.Clamp(config.MaxItemCount, 1, 10000)}");
            return;
        }
        if (fields.Length == 3 && fields[0] == "search" && int.TryParse(fields[1], out var page) && page is >= 0 and <= 100000)
        {
            var query = AlphaTransport.DecodeQuery(fields[2]);
            if (query is null) { Reply(character, id, "error", "Texto de búsqueda inválido."); return; }
            var items = AlphaCatalog.Search(query);
            var pages = Math.Max(1, (items.Length + AlphaRules.PageSize - 1) / AlphaRules.PageSize);
            page = Math.Min(page, pages - 1);
            var ids = string.Join(',', items.Skip(page * AlphaRules.PageSize).Take(AlphaRules.PageSize));
            Reply(character, id, "page", $"{page}/{pages}/{items.Length}/{ids}");
            return;
        }
        var ok = false;
        if (fields.Length == 2 && int.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out var amount))
        {
            if (fields[0] == "gold") ok = character.GrantAlphaGold(amount);
            if (fields[0] == "labor") ok = character.GrantAlphaLabor(amount);
            if (fields[0] == "honor") ok = character.GrantAlphaPoints(GamePointKind.Honor, amount);
            if (fields[0] == "vocation") ok = character.GrantAlphaPoints(GamePointKind.Vocation, amount);
        }
        else if (fields.Length == 4 && fields[0] == "item" && uint.TryParse(fields[1], out var templateId) &&
                 int.TryParse(fields[2], out var count) && byte.TryParse(fields[3], out var grade) && grade <= 12 &&
                 templateId != AlphaRules.KeyTemplateId && AlphaRules.ValidAmount(count, Math.Clamp(AppConfiguration.Instance.PrivateAlpha.MaxItemCount, 1, 10000)))
        {
            var template = ItemManager.Instance.GetTemplate(templateId);
            if (template is not null && (!template.Gradable || template.MaxEnchantableGrade < 0 || grade <= template.MaxEnchantableGrade))
                ok = character.GrantAlphaItems(templateId, count, template.Gradable ? grade : (byte)Math.Max(0, template.FixedGrade));
        }
        if (ok)
        {
            Log.Info("Private alpha grant character={0} request={1} operation={2}", character.Id, id, request);
            Reply(character, id, "ok", "Entrega completada y guardada.");
        }
        else Reply(character, id, "error", "No se pudo entregar: revisa cantidad, límite de saldo, grado y ranuras libres. Honor/vocación: 1–100000 por entrega. Las mercancías equipables no admiten entrega al bolso.");
    }

    public static bool SetAccess(Character target, uint actor, bool grant)
    {
        lock (GamePersistence.Sync)
        {
            if (!grant)
            {
                AlphaRepository.Revoke(target.Id);
                Reply(target, 0, "access", "0");
                Log.Info("Private alpha revoked character={0} actor={1}", target.Id, actor); return true;
            }
            if (!AppConfiguration.Instance.PrivateAlpha.Enabled) return false;
            using var connection = MySQL.CreateConnection(); using var transaction = connection.BeginTransaction();
            AlphaRepository.Grant(connection, transaction, target.Id, actor); transaction.Commit();
            Reply(target, 0, "access", "1");
            DeliverAuthorizedKey(target, actor); // Optional shortcut; a full bag never prevents access.
            Log.Info("Private alpha authorized character={0} actor={1}", target.Id, actor);
            return true;
        }
    }

    public static void DeliverAuthorizedKey(Character character, uint actor = 0)
    {
        if (!AppConfiguration.Instance.PrivateAlpha.Enabled) return;
        try
        {
            lock (GamePersistence.Sync)
            {
                if (!AlphaRepository.HasAccess(character.Id) || HasKey(character)) return;
                if (character.Inventory._itemContainers.Values.Any(c => c.Items.Any(i => i.TemplateId == AlphaRules.KeyTemplateId && i.Count > 0))) return;
                if (character.GrantAlphaItems(AlphaRules.KeyTemplateId, 1, 0, actor))
                    character.SendMessage("Alpha privada: puedes usar el icono de herramientas o esta llave para abrir el menú.");
                else character.SendMessage("Acceso alpha habilitado. Puedes usar el icono aunque no tengas espacio para la llave opcional.");
            }
        }
        catch (Exception exception) { Log.Error(exception, "Private alpha key delivery failed character={0}", character.Id); }
    }
}
