using System.Globalization;
using AAEmu.Commons.Utils.AAPak;

if (args.Length is < 2 or > 3)
{
    Console.Error.WriteLine(
        "Usage: PakIndexExport <game_pak> <new-output.tsv> [16-byte-key-file|32-hex-key]");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
var outputPath = Path.GetFullPath(args[1]);
if (!File.Exists(pakPath))
{
    Console.Error.WriteLine($"Package does not exist: {pakPath}");
    return 3;
}

if (File.Exists(outputPath))
{
    Console.Error.WriteLine($"Refusing to overwrite existing output: {outputPath}");
    return 4;
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
        return 5;
    }

    if (customKey.Length != 16)
    {
        Console.Error.WriteLine($"Custom key must contain exactly 16 bytes; found {customKey.Length}.");
        return 6;
    }
}

static string Clean(string value) => value.Replace('\t', ' ').Replace('\r', ' ').Replace('\n', ' ');

var pak = new AAPak(string.Empty);
if (customKey is not null)
    pak._header.SetCustomKey(customKey);
if (!pak.OpenPak(pakPath, openAsReadOnly: true))
{
    Console.Error.WriteLine("Could not open package read-only with the supplied key.");
    pak.ClosePak();
    return 7;
}

var outputDirectory = Path.GetDirectoryName(outputPath);
if (!string.IsNullOrEmpty(outputDirectory))
    Directory.CreateDirectory(outputDirectory);

try
{
    await using var stream = new FileStream(
        outputPath, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1024 * 1024, useAsync: true);
    await using var writer = new StreamWriter(stream);
    await writer.WriteLineAsync("name\tsize\toffset\tmd5\tcreate_time\tmodify_time\tsize_duplicate\tpadding_size\tdummy1\tdummy2");
    foreach (var entry in pak.pakFiles.Values.OrderBy(value => value.name, StringComparer.Ordinal))
    {
        var fields = new[]
        {
            Clean(entry.name),
            entry.size.ToString(CultureInfo.InvariantCulture),
            entry.offset.ToString(CultureInfo.InvariantCulture),
            Convert.ToHexString(entry.md5),
            entry.createTime.ToString(CultureInfo.InvariantCulture),
            entry.modifyTime.ToString(CultureInfo.InvariantCulture),
            entry.sizeDuplicate.ToString(CultureInfo.InvariantCulture),
            entry.paddingSize.ToString(CultureInfo.InvariantCulture),
            entry.dummy1.ToString(CultureInfo.InvariantCulture),
            entry.dummy2.ToString(CultureInfo.InvariantCulture),
        };
        await writer.WriteLineAsync(string.Join('\t', fields));
    }
}
catch
{
    if (File.Exists(outputPath))
        File.Delete(outputPath);
    throw;
}
finally
{
    pak.ClosePak();
}

Console.WriteLine($"Exported {pak.pakFiles.Count} index entries to {outputPath}");
return 0;
