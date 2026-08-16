using AAEmu.Game.Models.Game.Chat;

namespace AAEmu.Game.Core.Managers;

public sealed record ChatEventEntry(
    long Id,
    DateTime TimestampUtc,
    uint CharacterId,
    string CharacterName,
    string Channel,
    string TargetName,
    uint ZoneKey,
    string Message);

/// <summary>
/// Bounded in-memory journal for the local Control Center. It never persists chat to MySQL and
/// exposes snapshots only through the container-local WebApi.
/// </summary>
public static class ChatEventJournal
{
    private const int Capacity = 2000;
    private static readonly object Sync = new();
    private static readonly Queue<ChatEventEntry> Entries = new();
    private static long _nextId;

    public static void Record(uint characterId, string characterName, ChatType channel, string targetName, uint zoneKey, string message)
    {
        var entry = new ChatEventEntry(
            Interlocked.Increment(ref _nextId), DateTime.UtcNow, characterId, characterName,
            channel.ToString(), targetName ?? string.Empty, zoneKey, message ?? string.Empty);
        lock (Sync)
        {
            Entries.Enqueue(entry);
            while (Entries.Count > Capacity)
                Entries.Dequeue();
        }
    }

    public static IReadOnlyList<ChatEventEntry> ReadAfter(long afterId, int limit)
    {
        limit = Math.Clamp(limit, 1, 500);
        lock (Sync)
            return Entries.Where(entry => entry.Id > afterId).Take(limit).ToArray();
    }

    internal static void ClearForTests()
    {
        lock (Sync)
            Entries.Clear();
        Interlocked.Exchange(ref _nextId, 0);
    }
}
