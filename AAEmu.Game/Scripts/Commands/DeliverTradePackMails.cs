using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.Game.Scripts.Commands;

public class DeliverTradePackMails : ICommand
{
    public string[] CommandNames { get; set; } = ["delivertradepackmails", "deliver_trade_pack_mails"];

    public void OnLoad()
    {
        CommandManager.Instance.Register(CommandNames, this);
    }

    public string GetCommandLineHelp()
    {
        return "[character_name]";
    }

    public string GetCommandHelpText()
    {
        return "Immediately releases existing pending trade-pack reward mails for yourself or the named character. " +
               "It does not change the configured delay for future sales.";
    }

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        var targetId = character.Id;
        var targetName = character.Name;

        if (args.Length > 0)
        {
            targetId = NameManager.Instance.GetCharacterId(args[0].NormalizeName());
            targetName = NameManager.Instance.GetCharacterName(targetId);
            if (targetId == 0 || string.IsNullOrWhiteSpace(targetName))
            {
                CommandManager.SendErrorText(this, messageOutput, $"Character not found: {args[0]}");
                return;
            }
        }

        var result = MailManager.Instance.DeliverPendingSpecialtyMails(targetId);
        CommandManager.SendNormalText(this, messageOutput,
            $"Released {result.Released} pending trade-pack reward mail(s) for {targetName}; " +
            $"sent {result.Notified} immediate online notification(s).");
    }
}
