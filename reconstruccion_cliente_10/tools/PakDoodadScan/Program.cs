using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using AAEmu.Commons.Utils.AAPak;

if (args.Length is < 2 or > 3)
{
    Console.Error.WriteLine(
        "Usage: PakDoodadScan <game_pak> <comma-separated-doodad-ids> [16-byte-key-file|32-hex-key]");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
if (!File.Exists(pakPath))
{
    Console.Error.WriteLine($"Package does not exist: {pakPath}");
    return 3;
}

var requestedIds = new HashSet<uint>();
foreach (var token in args[1].Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
{
    if (!uint.TryParse(token, NumberStyles.None, CultureInfo.InvariantCulture, out var id))
    {
        Console.Error.WriteLine($"Invalid doodad id: {token}");
        return 4;
    }

    requestedIds.Add(id);
}

if (requestedIds.Count == 0)
{
    Console.Error.WriteLine("At least one doodad id is required.");
    return 5;
}

byte[]? customKey = null;
if (args.Length == 3)
{
    var keyArgument = args[2];
    if (File.Exists(keyArgument))
        customKey = await File.ReadAllBytesAsync(Path.GetFullPath(keyArgument));
    else if (keyArgument.Length == 32 && keyArgument.All(Uri.IsHexDigit))
        customKey = Convert.FromHexString(keyArgument);
    else
    {
        Console.Error.WriteLine("Custom key must be an existing 16-byte file or 32 hexadecimal digits.");
        return 6;
    }

    if (customKey.Length != 16)
    {
        Console.Error.WriteLine($"Custom key must contain exactly 16 bytes; found {customKey.Length}.");
        return 7;
    }
}

var pak = new AAPak(string.Empty);
if (customKey is not null)
    pak._header.SetCustomKey(customKey);

if (!pak.OpenPak(pakPath, openAsReadOnly: true))
{
    Console.Error.WriteLine("Could not open package read-only with the supplied key.");
    pak.ClosePak();
    return 8;
}

var cellPattern = new Regex(
    @"^game/worlds/main_world/level_design/cells/(?<x>\d{3})_(?<y>\d{3})/doodad\.g$",
    RegexOptions.Compiled | RegexOptions.CultureInvariant | RegexOptions.IgnoreCase);
var typePattern = new Regex(@"^\s*type\s+(?<id>\d+)\s*$", RegexOptions.Compiled | RegexOptions.Multiline);
var positionPattern = new Regex(
    @"^\s*pos\s+\(\s*x\s+(?<x>[-+0-9.eE]+),\s*y\s+(?<y>[-+0-9.eE]+),\s*z\s+(?<z>[-+0-9.eE]+)\s*\)\s*$",
    RegexOptions.Compiled | RegexOptions.Multiline);
var orientationPattern = new Regex(
    @"^\s*ori\s+\(\s*x\s+(?<x>[-+0-9.eE]+),\s*y\s+(?<y>[-+0-9.eE]+),\s*z\s+(?<z>[-+0-9.eE]+),\s*w\s+(?<w>[-+0-9.eE]+)\s*\)\s*$",
    RegexOptions.Compiled | RegexOptions.Multiline);
var scalePattern = new Regex(@"^\s*scale\s+(?<scale>[-+0-9.eE]+)\s*$", RegexOptions.Compiled | RegexOptions.Multiline);

Console.WriteLine("doodad_id,entry,cell_x,cell_y,x,y,z,rotation_x,rotation_y,rotation_z,yaw_degrees,scale");
var foundIds = new HashSet<uint>();

try
{
    foreach (var entry in pak.pakFiles.Values.OrderBy(candidate => candidate.name, StringComparer.Ordinal))
    {
        var cellMatch = cellPattern.Match(entry.name);
        if (!cellMatch.Success)
            continue;

        using var source = pak.ExportFileAsStream(entry);
        using var reader = new StreamReader(source, Encoding.UTF8, detectEncodingFromByteOrderMarks: true);
        var text = await reader.ReadToEndAsync();
        var blocks = Regex.Split(text, @"(?m)(?=^doodad\s*$)");
        foreach (var block in blocks)
        {
            var typeMatch = typePattern.Match(block);
            if (!typeMatch.Success ||
                !uint.TryParse(typeMatch.Groups["id"].Value, CultureInfo.InvariantCulture, out var doodadId) ||
                !requestedIds.Contains(doodadId))
                continue;

            var positionMatch = positionPattern.Match(block);
            var orientationMatch = orientationPattern.Match(block);
            var scaleMatch = scalePattern.Match(block);
            if (!positionMatch.Success || !orientationMatch.Success || !scaleMatch.Success)
                throw new InvalidDataException($"Incomplete doodad block for {doodadId} in {entry.name}.");

            var cellX = int.Parse(cellMatch.Groups["x"].Value, CultureInfo.InvariantCulture);
            var cellY = int.Parse(cellMatch.Groups["y"].Value, CultureInfo.InvariantCulture);
            var localX = ParseDouble(positionMatch, "x");
            var localY = ParseDouble(positionMatch, "y");
            var z = ParseDouble(positionMatch, "z");
            var rotationX = ParseDouble(orientationMatch, "x");
            var rotationY = ParseDouble(orientationMatch, "y");
            var rotationZ = ParseDouble(orientationMatch, "z");
            var rotationW = ParseDouble(orientationMatch, "w");
            var yaw = Math.Atan2(
                2d * ((rotationW * rotationZ) + (rotationX * rotationY)),
                1d - (2d * ((rotationY * rotationY) + (rotationZ * rotationZ)))) * 180d / Math.PI;
            var scale = ParseDouble(scaleMatch, "scale");

            Console.WriteLine(string.Join(',',
                doodadId.ToString(CultureInfo.InvariantCulture),
                entry.name,
                cellX.ToString(CultureInfo.InvariantCulture),
                cellY.ToString(CultureInfo.InvariantCulture),
                Format((cellX * 1024d) + localX),
                Format((cellY * 1024d) + localY),
                Format(z),
                Format(rotationX),
                Format(rotationY),
                Format(rotationZ),
                Format(yaw),
                Format(scale)));
            foundIds.Add(doodadId);
        }
    }
}
finally
{
    pak.ClosePak();
}

var missingIds = requestedIds.Except(foundIds).Order().ToArray();
if (missingIds.Length > 0)
{
    Console.Error.WriteLine($"Doodad ids not found in main_world cell data: {string.Join(',', missingIds)}");
    return 9;
}

return 0;

static double ParseDouble(Match match, string group) =>
    double.Parse(match.Groups[group].Value, NumberStyles.Float, CultureInfo.InvariantCulture);

static string Format(double value) => value.ToString("0.######", CultureInfo.InvariantCulture);
