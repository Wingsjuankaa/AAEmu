using System.Globalization;
using System.Text;

namespace AAEmu.Game.Models.Game.PrivateAlpha;

/// <summary>Self-only extension over the measured r575 48-byte channel-name field.</summary>
public sealed class AlphaTransport
{
    public const string Prefix = "aa10ap1:";
    public const int ChunkSize = 24;
    private uint _id;
    private int _next;
    private string[] _parts;
    private DateTime _expires;
    private readonly HashSet<uint> _seen = [];
    public static bool IsReserved(string name) => name.StartsWith(Prefix, StringComparison.Ordinal);

    // One session accepts each id at most once. Bounded memory; reconnect resets the transport.
    public string Receive(string name, string password, bool create, DateTime now, out uint requestId)
    {
        requestId = 0;
        if (!IsReserved(name) || name.Length > 48 || password.Length != 0 || create ||
            name.Any(c => c > 127) || _seen.Count >= 10000) return null;
        var p = name[Prefix.Length..].Split(':', 4);
        if (p.Length != 4 || !uint.TryParse(p[0], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var id) || id == 0 ||
            !int.TryParse(p[1], out var index) || !int.TryParse(p[2], out var count) ||
            count is < 1 or > 12 || index < 1 || index > count || p[3].Length is < 1 or > ChunkSize ||
            (index < count && p[3].Length != ChunkSize) || _seen.Contains(id)) return null;
        if (_parts is null || now > _expires || _id != id)
        {
            if (index != 1) return null;
            _id = id; _next = 1; _parts = new string[count]; _expires = now.AddSeconds(5);
        }
        if (_next != index || count != _parts.Length) { _parts = null; _seen.Add(id); return null; }
        _parts[index - 1] = p[3]; _next++;
        if (index != count) return null;
        var payload = string.Concat(_parts);
        _parts = null; _seen.Add(id); requestId = id;
        return payload;
    }

    public static string DecodeQuery(string hex)
    {
        if (hex.Length > 192 || hex.Length % 2 != 0) return null;
        try { return new UTF8Encoding(false, true).GetString(Convert.FromHexString(hex)); }
        catch (Exception e) when (e is FormatException or DecoderFallbackException) { return null; }
    }
}
