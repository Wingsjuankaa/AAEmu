using System.Text;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.PrivateAlpha;
using AAEmu.Game.Utils.Scripts.SubCommands;

namespace AAEmu.Game.Models.Game.GmPanel;

public sealed record GmPanelEntry(string Name, string Category, string Description, string Example, bool Confirm, string Help);

/// <summary>The loaded command registry owns availability, syntax and permissions.</summary>
public static class GmPanelCatalog
{
    public const int MinimumAccess = 50;
    public static bool CanUse(int access) => access >= MinimumAccess;

    public static GmPanelEntry[] Get(int access)
    {
        if (!CanUse(access)) return [];
        var manager = CommandManager.Instance;
        return manager.GetCommandKeys().Order(StringComparer.Ordinal).Where(name =>
            AccessLevelManager.Instance.GetLevel(name) <= access).Select(name =>
        {
            var command = manager.GetCommandInterfaceByName(name);
            var meta = GmPanelDescriptions.Get(command.GetType().Name);
            var help = new StringBuilder().AppendLine("/" + name + " " + command.GetCommandLineHelp())
                .AppendLine(command.GetCommandHelpText()).AppendLine("Alias: " + string.Join(", ", command.CommandNames));
            if (command is SubCommandBase tree)
                foreach (var line in tree.DescribeTree(name)) help.AppendLine(line);
            return new GmPanelEntry(name, meta.Category, meta.Description, meta.Example, meta.Confirm, help.ToString());
        }).ToArray();
    }

    public static string DecodeCommand(string hex)
    {
        // Same measured transport as alpha, bounded to twelve 24-byte fragments.
        if (hex.Length is 0 or > 260 || hex.Length % 2 != 0) return null;
        try
        {
            var value = new UTF8Encoding(false, true).GetString(Convert.FromHexString(hex));
            if (value.Any(char.IsControl) || value.StartsWith('/') || value.Trim() != value) return null;
            return value;
        }
        catch (Exception e) when (e is FormatException or DecoderFallbackException) { return null; }
    }

    public static string SearchKey(string value) => AlphaRules.Normalize(value);
}
