using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using AAEmu.Commons.Utils.AAPak;

if (args.Length is < 1 or > 2)
{
    Console.Error.WriteLine("Usage: PakReturnPointScan <game_pak> [16-byte-key-file|32-hex-key]");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
if (!File.Exists(pakPath))
{
    Console.Error.WriteLine($"Package does not exist: {pakPath}");
    return 3;
}

byte[]? customKey = null;
if (args.Length == 2)
{
    var keyArgument = args[1];
    if (File.Exists(keyArgument))
        customKey = await File.ReadAllBytesAsync(Path.GetFullPath(keyArgument));
    else if (keyArgument.Length == 32 && keyArgument.All(Uri.IsHexDigit))
        customKey = Convert.FromHexString(keyArgument);
    else
    {
        Console.Error.WriteLine("Custom key must be an existing 16-byte file or 32 hexadecimal digits.");
        return 4;
    }

    if (customKey.Length != 16)
    {
        Console.Error.WriteLine($"Custom key must contain exactly 16 bytes; found {customKey.Length}.");
        return 5;
    }
}

var pak = new AAPak(string.Empty);
if (customKey is not null)
    pak._header.SetCustomKey(customKey);

if (!pak.OpenPak(pakPath, openAsReadOnly: true))
{
    Console.Error.WriteLine("Could not open package read-only with the supplied key.");
    pak.ClosePak();
    return 6;
}

var entryPattern = new Regex(
    @"^game/worlds/main_world/level_design/zone/(?<zone>\d+)/world_server/return_point\.g$",
    RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);
var objectPattern = new Regex(@"(?ms)^object\s*\r?\n(?<body>.*?)(?=^object\s*$|\z)", RegexOptions.Compiled);
var namePattern = new Regex(@"^\s*name\s+ReturnPoint_(?<name>\S+)\s*$", RegexOptions.Compiled | RegexOptions.Multiline | RegexOptions.IgnoreCase);
var positionPattern = new Regex(
    @"^\s*pos\s+\(\s*x\s+(?<x>[-+0-9.eE]+),\s*y\s+(?<y>[-+0-9.eE]+),\s*z\s+(?<z>[-+0-9.eE]+)\s*\)\s*$",
    RegexOptions.Compiled | RegexOptions.Multiline | RegexOptions.IgnoreCase);
var rotationPattern = new Regex(@"^\s*zRot\s+(?<zrot>[-+0-9.eE]+)\s*$", RegexOptions.Compiled | RegexOptions.Multiline | RegexOptions.IgnoreCase);
var radiusPattern = new Regex(@"^\s*radius\s+(?<radius>[-+0-9.eE]+)\s*$", RegexOptions.Compiled | RegexOptions.Multiline | RegexOptions.IgnoreCase);

Console.WriteLine("zone_id,editor_name,x,y,z,z_rot,radius,entry");
try
{
    foreach (var entry in pak.pakFiles.Values.OrderBy(candidate => candidate.name, StringComparer.Ordinal))
    {
        var entryMatch = entryPattern.Match(entry.name);
        if (!entryMatch.Success)
            continue;

        using var source = pak.ExportFileAsStream(entry);
        using var reader = new StreamReader(source, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var text = await reader.ReadToEndAsync();
        foreach (Match objectMatch in objectPattern.Matches(text))
        {
            var body = objectMatch.Groups["body"].Value;
            var nameMatch = namePattern.Match(body);
            var positionMatch = positionPattern.Match(body);
            if (!nameMatch.Success || !positionMatch.Success)
                continue;

            var rotationMatch = rotationPattern.Match(body);
            var radiusMatch = radiusPattern.Match(body);
            Console.WriteLine(string.Join(',',
                entryMatch.Groups["zone"].Value,
                EscapeCsv(nameMatch.Groups["name"].Value),
                Format(ParseDouble(positionMatch, "x")),
                Format(ParseDouble(positionMatch, "y")),
                Format(ParseDouble(positionMatch, "z")),
                rotationMatch.Success ? Format(ParseDouble(rotationMatch, "zrot")) : "0",
                radiusMatch.Success ? Format(ParseDouble(radiusMatch, "radius")) : "0",
                EscapeCsv(entry.name)));
        }
    }
}
finally
{
    pak.ClosePak();
}

return 0;

static double ParseDouble(Match match, string group) =>
    double.Parse(match.Groups[group].Value, NumberStyles.Float, CultureInfo.InvariantCulture);

static string Format(double value) => value.ToString("0.######", CultureInfo.InvariantCulture);

static string EscapeCsv(string value) =>
    value.IndexOfAny([',', '"', '\r', '\n']) >= 0 ? $"\"{value.Replace("\"", "\"\"")}\"" : value;
