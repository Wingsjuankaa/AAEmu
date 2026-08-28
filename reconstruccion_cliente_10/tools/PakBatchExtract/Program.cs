using System.Security.Cryptography;
using AAEmu.Commons.Utils.AAPak;

if (args.Length != 3)
{
    Console.Error.WriteLine("Usage: PakBatchExtract <game_pak> <entry-list> <output-directory>");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
var entryListPath = Path.GetFullPath(args[1]);
var outputDirectory = Path.GetFullPath(args[2]);

if (!File.Exists(pakPath) || !File.Exists(entryListPath))
{
    Console.Error.WriteLine("The package and entry list must already exist.");
    return 3;
}

var requestedEntries = (await File.ReadAllLinesAsync(entryListPath))
    .Select(line => line.Trim().Replace('\\', '/'))
    .Where(line => line.Length > 0 && !line.StartsWith('#'))
    .Distinct(StringComparer.OrdinalIgnoreCase)
    .Order(StringComparer.Ordinal)
    .ToArray();
if (requestedEntries.Length == 0)
{
    Console.Error.WriteLine("The entry list is empty.");
    return 4;
}

var pak = new AAPak(string.Empty);
if (!pak.OpenPak(pakPath, openAsReadOnly: true))
{
    Console.Error.WriteLine("Could not open package read-only.");
    pak.ClosePak();
    return 5;
}

try
{
    foreach (var entryName in requestedEntries)
    {
        if (!pak.GetFileByName(entryName, out var entry))
        {
            Console.Error.WriteLine($"Package entry was not found: {entryName}");
            return 6;
        }

        var relativeName = entryName.StartsWith("game/", StringComparison.OrdinalIgnoreCase)
            ? entryName["game/".Length..]
            : entryName;
        var outputPath = Path.GetFullPath(Path.Combine(outputDirectory, relativeName));
        if (!outputPath.StartsWith(outputDirectory + Path.DirectorySeparatorChar,
                StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine($"Entry escapes output directory: {entryName}");
            return 7;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);
        await using (var source = pak.ExportFileAsStream(entry))
        await using (var target = new FileStream(
                         outputPath, FileMode.Create, FileAccess.Write, FileShare.None,
                         bufferSize: 1024 * 1024, useAsync: true))
        {
            await source.CopyToAsync(target);
            await target.FlushAsync();
        }

        var info = new FileInfo(outputPath);
        if (info.Length != entry.size)
        {
            Console.Error.WriteLine(
                $"Extracted size mismatch for {entryName}: entry={entry.size}, output={info.Length}");
            return 8;
        }

        await using var extracted = File.OpenRead(outputPath);
        var hash = Convert.ToHexString(await SHA256.HashDataAsync(extracted));
        Console.WriteLine($"{entryName};{info.Length};{hash}");
    }
}
finally
{
    pak.ClosePak();
}

return 0;
