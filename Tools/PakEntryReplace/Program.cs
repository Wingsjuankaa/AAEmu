using System.Security.Cryptography;
using AAEmu.Commons.Utils.AAPak;

if (args.Length != 4)
{
    Console.Error.WriteLine(
        "Usage: PakEntryReplace <game_pak> <entry> <same-size-replacement> <expected-current-sha256>");
    return 2;
}

var pakPath = Path.GetFullPath(args[0]);
var entryName = args[1];
var replacementPath = Path.GetFullPath(args[2]);
var expectedCurrentHash = args[3].ToUpperInvariant();

if (!File.Exists(pakPath) || !File.Exists(replacementPath))
{
    Console.Error.WriteLine("Package or replacement file does not exist.");
    return 3;
}

if (expectedCurrentHash.Length != 64 || expectedCurrentHash.Any(character => !Uri.IsHexDigit(character)))
{
    Console.Error.WriteLine("Expected hash must be a SHA-256 hexadecimal string.");
    return 4;
}

static async Task<string> HashAsync(Stream stream)
{
    stream.Position = 0;
    return Convert.ToHexString(await SHA256.HashDataAsync(stream));
}

var replacementInfo = new FileInfo(replacementPath);
string replacementHash;
await using (var replacement = replacementInfo.OpenRead())
    replacementHash = await HashAsync(replacement);

var readPak = new AAPak(pakPath, openAsReadOnly: true);
if (!readPak.isOpen || !readPak.GetFileByName(entryName, out var readInfo))
{
    Console.Error.WriteLine($"Could not open package entry: {entryName}");
    readPak.ClosePak();
    return 5;
}

string currentHash;
using (var current = readPak.ExportFileAsStream(readInfo))
    currentHash = await HashAsync(current);
var currentSize = readInfo.size;
readPak.ClosePak();

if (currentHash.Equals(replacementHash, StringComparison.Ordinal))
{
    Console.WriteLine($"Already patched {entryName} ({currentSize} bytes, SHA-256 {currentHash})");
    return 0;
}

if (!currentHash.Equals(expectedCurrentHash, StringComparison.Ordinal))
{
    Console.Error.WriteLine(
        $"Current entry hash mismatch. Expected {expectedCurrentHash}, found {currentHash}. Refusing to write.");
    return 6;
}

if (replacementInfo.Length != currentSize)
{
    Console.Error.WriteLine(
        $"Refusing non-size-preserving replacement: entry={currentSize}, replacement={replacementInfo.Length}");
    return 7;
}

var writablePak = new AAPak(pakPath, openAsReadOnly: false);
if (!writablePak.isOpen || !writablePak.GetFileByName(entryName, out var writableInfo))
{
    Console.Error.WriteLine($"Could not open package entry for replacement: {entryName}");
    writablePak.ClosePak();
    return 8;
}

await using (var replacement = replacementInfo.OpenRead())
{
    if (!writablePak.ReplaceFile(ref writableInfo, replacement, replacementInfo.LastWriteTimeUtc))
    {
        Console.Error.WriteLine($"Package rejected replacement: {entryName}");
        writablePak.ClosePak();
        return 9;
    }
}
writablePak.ClosePak();

var verifyPak = new AAPak(pakPath, openAsReadOnly: true);
if (!verifyPak.isOpen || !verifyPak.GetFileByName(entryName, out var verifyInfo))
{
    Console.Error.WriteLine($"Could not reopen replaced entry: {entryName}");
    verifyPak.ClosePak();
    return 10;
}

string actualHash;
using (var actual = verifyPak.ExportFileAsStream(verifyInfo))
    actualHash = await HashAsync(actual);
verifyPak.ClosePak();

if (verifyInfo.size != replacementInfo.Length || !actualHash.Equals(replacementHash, StringComparison.Ordinal))
{
    Console.Error.WriteLine(
        $"Post-write verification failed: size={verifyInfo.size}, expectedHash={replacementHash}, actualHash={actualHash}");
    return 11;
}

Console.WriteLine($"Replaced and verified {entryName} ({verifyInfo.size} bytes, SHA-256 {actualHash})");
return 0;
