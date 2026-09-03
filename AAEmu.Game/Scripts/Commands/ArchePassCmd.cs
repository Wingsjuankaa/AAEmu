using System.Globalization;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;
using NLog;

namespace AAEmu.Game.Scripts.Commands;

public class ArchePassCmd : ICommand
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
    public string[] CommandNames { get; set; } = ["archepass"];

    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "addpoints self <amount>";
    public string GetCommandHelpText() =>
        "GM: adds positive points to your active ArchePass, capped at its final tier. Does not claim rewards.";

    public static bool TryParseAddPoints(string[] args, out int amount)
    {
        amount = 0;
        return args is { Length: 3 } &&
            string.Equals(args[0], "addpoints", StringComparison.OrdinalIgnoreCase) &&
            string.Equals(args[1], "self", StringComparison.OrdinalIgnoreCase) &&
            int.TryParse(args[2], NumberStyles.None, CultureInfo.InvariantCulture, out amount) && amount > 0;
    }

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        // Keep the GM gate even when invoked outside the chat command dispatcher.
        if (character is null || CharacterManager.Instance.GetEffectiveAccessLevel(character) < 100)
        {
            CommandManager.SendErrorText(this, messageOutput, "GM access level 100 required.");
            return;
        }

        if (!TryParseAddPoints(args, out var amount))
        {
            CommandManager.SendErrorText(this, messageOutput,
                "Usage: /archepass addpoints self <amount>; amount must be 1..2147483647.");
            return;
        }

        if (!ArchePassManager.Instance.TryAddPoints(character, amount, out var change))
        {
            CommandManager.SendErrorText(this, messageOutput,
                "No available active ArchePass, feature disabled, or persistence unavailable. Start a valid registered pass first.");
            return;
        }

        Logger.Info("GM ArchePass points: character={0} account={1} type={2} requested={3} applied={4} before={5} after={6}",
            character.Name, character.AccountId, change.Type, amount, change.AppliedPoints, change.PreviousPoint, change.Point);
        messageOutput.SendMessage($"ArchePass {change.Type}: +{change.AppliedPoints} points; total {change.Point}; tier {change.Tier}." +
            (change.AppliedPoints < amount ? " Final tier point cap reached." : "") +
            " Rewards remain unclaimed. Saved with normal character autosave/logout.");
    }
}
