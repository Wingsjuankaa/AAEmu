using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;
using NLog;

namespace AAEmu.Game.Scripts.Commands;

public sealed class FishSpots : ICommand
{
    private static readonly Logger Log = LogManager.GetCurrentClassLogger();
    public string[] CommandNames { get; set; } = ["fishspots"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "[on|off]";
    public string GetCommandHelpText() => "Muestra los bancos de pesca presentes en tu mundo e instancia. /fishspots off restaura el radar normal.";

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        if (CharacterManager.Instance.GetEffectiveAccessLevel(character) < 100)
        { messageOutput.SendMessage("Este comando requiere privilegios GM."); return; }
        if (args.Length > 1 || (args.Length == 1 && args[0] is not ("on" or "off")))
        { CommandManager.SendDefaultHelpText(this, messageOutput); return; }
        var enabled = args.Length == 0 || args[0] == "on";
        var count = RadarManager.Instance.SetAllFishSchools(character, enabled);
        messageOutput.SendMessage(enabled
            ? $"Mapa de pesca activado: {count} bancos presentes en tu mundo e instancia. Abre el mapa (M). /fishspots off para desactivar."
            : "Mapa de pesca GM desactivado. Se conserva el radar normal si está activo.");
        Log.Info("FishSpots character={0} instance={1} enabled={2} schools={3}",
            character.Id, character.Transform.InstanceId, enabled, count);
    }
}
