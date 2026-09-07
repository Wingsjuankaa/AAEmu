using System.Globalization;

namespace AAEmu.Game.Models.Game.Items.Services;

/// <summary>Custom, self-only RPC over native CSJoinUserChatChannel strings.
/// Native r575 copies 48 name bytes and 6 password bytes. No channel is joined.</summary>
public sealed class EquipSlotReinforceBatchTransport
{
    public const string Prefix = "aa10ip3:";
    public const string CancelPrefix = "aa10ip3cancel:";
    public const int ChunkSize = 23;
    private uint _id;
    private string[] _parts;
    private DateTime _expires;
    private uint _completedId;
    private DateTime _completedExpires;

    public static bool IsReserved(string name) => name.StartsWith(Prefix, StringComparison.Ordinal) ||
        name.StartsWith(CancelPrefix, StringComparison.Ordinal);

    // Caller serializes access per authenticated character. Invalid/incomplete frames never start a cast.
    public EquipSlotReinforceBatchRequest Receive(string name, string password, bool create, DateTime now,
        out uint cancelledId)
    {
        cancelledId = 0;
        if (name.Length > 48 || password.Length != 0 || create) return null;
        if (name.StartsWith(CancelPrefix, StringComparison.Ordinal))
        {
            if (uint.TryParse(name[CancelPrefix.Length..], NumberStyles.None, CultureInfo.InvariantCulture,
                    out var id) && id != 0)
            {
                cancelledId = id;
                if (_id == id) _parts = null;
                _completedId = id; _completedExpires = now.AddSeconds(10);
            }
            return null;
        }
        if (!name.StartsWith(Prefix, StringComparison.Ordinal)) return null;
        var fields = name[Prefix.Length..].Split(':', 4);
        if (fields.Length != 4 || !uint.TryParse(fields[0], NumberStyles.None, CultureInfo.InvariantCulture, out var requestId) || requestId == 0 ||
            !int.TryParse(fields[1], NumberStyles.None, CultureInfo.InvariantCulture, out var index) ||
            !int.TryParse(fields[2], NumberStyles.None, CultureInfo.InvariantCulture, out var count) ||
            count is < 1 or > 11 || index < 1 || index > count || fields[3].Length is < 1 or > ChunkSize ||
            (index < count && fields[3].Length != ChunkSize)) return null;
        if (_completedId == requestId && now <= _completedExpires) return null;
        if (_parts is null || now > _expires || _id != requestId)
        {
            // TCP is ordered; a tail without its first frame cannot authorize anything.
            if (index != 1) return null;
            _id = requestId; _parts = new string[count]; _expires = now.AddSeconds(5);
        }
        if (_parts.Length != count || (_parts[index - 1] is { } previous && previous != fields[3]))
        {
            _parts = null; return null;
        }
        _parts[index - 1] = fields[3];
        if (_parts.Any(p => p is null)) return null;
        var payload = string.Concat(_parts);
        _parts = null; _completedId = requestId; _completedExpires = now.AddSeconds(10);
        var request = EquipSlotReinforceBatchRequest.Parse(payload);
        return request?.RequestId == requestId ? request : null;
    }
}
