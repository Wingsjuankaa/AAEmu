using System.Globalization;

namespace AAEmu.Game.Models.Game.BugReports;

public sealed class BugReportTransport
{
    public const string Prefix = "aa10br1:";
    private uint _id;
    private int _next;
    private string[] _parts;
    private DateTime _expires;
    private readonly HashSet<uint> _seen = [];
    public static bool IsReserved(string name) => name.StartsWith(Prefix, StringComparison.Ordinal);
    public string Receive(string name, string password, bool create, DateTime now, out uint id)
    {
        id = 0;
        if (!IsReserved(name) || name.Length > 48 || password.Length != 0 || create ||
            name.Any(c => c > 127) || _seen.Count >= 10000) return null;
        var p = name[Prefix.Length..].Split(':', 4);
        if (p.Length != 4 || !uint.TryParse(p[0], NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var request) || request == 0 ||
            !int.TryParse(p[1], out var index) || !int.TryParse(p[2], out var count) || count is < 1 or > 260 ||
            index < 1 || index > count || p[3].Length is < 1 or > 20 || index < count && p[3].Length != 20 || _seen.Contains(request)) return null;
        if (_parts is null || now > _expires || request != _id)
        {
            if (index != 1) return null;
            _id = request; _next = 1; _parts = new string[count]; _expires = now.AddSeconds(30);
        }
        if (index != _next || count != _parts.Length) { _parts = null; _seen.Add(request); return null; }
        _parts[index - 1] = p[3]; _next++;
        if (index != count) return null;
        var payload = string.Concat(_parts); _parts = null; _seen.Add(request); id = request;
        return payload;
    }
}
