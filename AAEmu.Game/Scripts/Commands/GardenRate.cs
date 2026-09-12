using System.Globalization;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;
using NLog;

namespace AAEmu.Game.Scripts.Commands;

public sealed class GardenRate : ICommand
{
    public string[] CommandNames { get; set; } = ["gardenrate"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "[1..1000]";
    public string GetCommandHelpText() =>
        "Consulta o cambia el multiplicador global de puntos ganados en Garden. 1 restaura el valor normal; se reinicia a 1 al reiniciar Game.";

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        if (args.Length == 0)
        {
            messageOutput.SendMessage($"Garden: multiplicador global x{GardenScoreRate.Multiplier}. /gardenrate 1 restaura el valor normal.");
            return;
        }
        if (args.Length != 1 || !int.TryParse(args[0], NumberStyles.Integer, CultureInfo.InvariantCulture, out var rate) ||
            !GardenScoreRate.TrySet(rate))
        {
            CommandManager.SendErrorText(this, messageOutput, "Usa /gardenrate con un entero de 1 a 1000.");
            return;
        }
        messageOutput.SendMessage($"Garden: ganancias de todos los jugadores x{rate}, desde ahora. Reiniciar Game restaura x1.");
        LogManager.GetCurrentClassLogger().Info("Garden rate changed by character={0}: multiplier={1}", character.Id, rate);
    }
}
