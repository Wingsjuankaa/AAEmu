using System.Security.Cryptography;
using AAEmu.Commons.Utils.AAPak;

if (args.Length is < 3 or > 4)
{
    Console.Error.WriteLine(
        "Usage: PakEntryExtract <game_pak> <entry> <new-output> [16-byte-key-file|32-hex-key]");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
var entryName = args[1];
var outputPath = Path.GetFullPath(args[2]);

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
if (args.Length == 4)
{
    var keyArgument = args[3];
    if (File.Exists(keyArgument))
    {
        customKey = await File.ReadAllBytesAsync(Path.GetFullPath(keyArgument));
    }
    else if (keyArgument.Length == 32 && keyArgument.All(Uri.IsHexDigit))
    {
        customKey = Convert.FromHexString(keyArgument);
    }
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

var pak = new AAPak(string.Empty);
if (customKey is not null)
    pak._header.SetCustomKey(customKey);

if (!pak.OpenPak(pakPath, openAsReadOnly: true))
{
    Console.Error.WriteLine("Could not open package read-only with the supplied key.");
    pak.ClosePak();
    return 7;
}

if (!pak.GetFileByName(entryName, out var entry))
{
    var leaf = Path.GetFileName(entryName);
    var sameNameMatches = pak.pakFiles.Values
        .Where(candidate => Path.GetFileName(candidate.name)
            .Equals(leaf, StringComparison.OrdinalIgnoreCase))
        .Select(candidate => candidate.name)
        .Take(20)
        .ToArray();
    var relatedMatches = pak.pakFiles.Values
        .Where(candidate => candidate.name.Contains("compact", StringComparison.OrdinalIgnoreCase)
            || candidate.name.Contains("sqlite", StringComparison.OrdinalIgnoreCase))
        .Select(candidate => candidate.name)
        .Take(100)
        .ToArray();
    Console.Error.WriteLine(
        $"Package opened with {pak.pakFiles.Count} files, but entry was not found: {entryName}");
    if (sameNameMatches.Length > 0)
        Console.Error.WriteLine($"Same-name candidates: {string.Join(", ", sameNameMatches)}");
    if (relatedMatches.Length > 0)
        Console.Error.WriteLine($"Compact/SQLite candidates: {string.Join(", ", relatedMatches)}");
    pak.ClosePak();
    return 8;
}

var outputDirectory = Path.GetDirectoryName(outputPath);
if (!string.IsNullOrEmpty(outputDirectory))
    Directory.CreateDirectory(outputDirectory);

try
{
    using var source = pak.ExportFileAsStream(entry);
    await using var target = new FileStream(
        outputPath,
        FileMode.CreateNew,
        FileAccess.Write,
        FileShare.None,
        bufferSize: 1024 * 1024,
        useAsync: true);
    await source.CopyToAsync(target);
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

await using var extracted = File.OpenRead(outputPath);
var hash = Convert.ToHexString(await SHA256.HashDataAsync(extracted));
var size = new FileInfo(outputPath).Length;
if (size != entry.size)
{
    Console.Error.WriteLine($"Extracted size mismatch: entry={entry.size}, output={size}");
    return 9;
}

Console.WriteLine($"Extracted {entryName} ({size} bytes, SHA-256 {hash})");
return 0;
