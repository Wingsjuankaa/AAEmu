namespace AAEmu.Game.Core.Managers;

/// <summary>Serializes full-save transactions and immediate inventory/progression commits.
/// Acquired before character wallet or container locks; never held while publishing packets.</summary>
internal static class GamePersistence
{
    internal static readonly object Sync = new();
}
