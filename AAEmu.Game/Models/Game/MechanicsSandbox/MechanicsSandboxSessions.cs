using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

/// <summary>The world cache can retain a disconnected avatar; only the active transport owns a session.</summary>
internal static class MechanicsSandboxSessions
{
    internal static Character Find(string name, IEnumerable<GameConnection> connections) =>
        connections.Select(connection => connection.ActiveChar).FirstOrDefault(character =>
            character != null && string.Equals(character.Name, name, StringComparison.Ordinal));

    internal static bool IsCurrent(Character character, IEnumerable<GameConnection> connections) =>
        character != null && connections.Any(connection => ReferenceEquals(connection.ActiveChar, character));
}
