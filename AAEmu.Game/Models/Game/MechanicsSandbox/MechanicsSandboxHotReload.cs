using System.Reflection.Metadata;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using AAEmu.Game.Models;

[assembly: MetadataUpdateHandler(typeof(AAEmu.Game.Models.Game.MechanicsSandbox.MechanicsSandboxHotReload))]

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

/// <summary>
/// Observes CLR metadata updates in the real Game assembly. It does not replace skill code,
/// reload game data, change mechanics, or send chat. Ordinary configurations keep this dormant.
/// </summary>
public static class MechanicsSandboxHotReload
{
    private static long s_updateCount;
    private static long s_lastUpdateUtcTicks;

    public sealed record RuntimeStatus(int Pid, bool HotReloadSupported, bool RunningUnderWatch,
        long UpdateCount, DateTimeOffset? LastUpdateUtc, string DiagnosticStamp, string RuntimeVersion);

    public static bool IsEnabled(MechanicsSandboxConfig config) =>
        config is { Enabled: true, CharacterId: > 0, AccountId: > 0 } &&
        !string.IsNullOrWhiteSpace(config.CharacterName);

    /// <summary>No derived caches are owned by this diagnostic observer.</summary>
    public static void ClearCache(Type[] updatedTypes) { }

    /// <summary>Called by the CLR after applying a supported update to this assembly.</summary>
    public static void UpdateApplication(Type[] updatedTypes)
    {
        if (!IsEnabled(AppConfiguration.Instance.MechanicsSandbox))
            return;
        Interlocked.Exchange(ref s_lastUpdateUtcTicks, DateTimeOffset.UtcNow.UtcTicks);
        Interlocked.Increment(ref s_updateCount);
    }

    /// <summary>
    /// A method-body-only development probe. Changing/reverting its literal while watch is running
    /// lets the runtime endpoint demonstrate actual CLR updates with an unchanged process ID.
    /// </summary>
    [MethodImpl(MethodImplOptions.NoInlining)]
    public static string DiagnosticStamp() => "aa10-real-runtime-v1";

    public static RuntimeStatus Snapshot()
    {
        var ticks = Interlocked.Read(ref s_lastUpdateUtcTicks);
        return new RuntimeStatus(Environment.ProcessId, MetadataUpdater.IsSupported,
            Environment.GetEnvironmentVariable("DOTNET_WATCH") == "1",
            Interlocked.Read(ref s_updateCount),
            ticks == 0 ? null : new DateTimeOffset(ticks, TimeSpan.Zero),
            DiagnosticStamp(), RuntimeInformation.FrameworkDescription);
    }
}
