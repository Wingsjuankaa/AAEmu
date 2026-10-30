using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;
using System.Text.Json;

namespace AAEmu.Game.Scripts.Commands;

public sealed class MechanicsSandbox : ICommand
{
    public string[] CommandNames { get; set; } = ["sandbox"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "<begin|status|reset|clear>";
    public string GetCommandHelpText() => "Controla el escenario de desarrollo del personaje exclusivo configurado.";
    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        if (CharacterManager.Instance.GetEffectiveAccessLevel(character) < 100)
        {
            CommandManager.SendErrorText(this, messageOutput, "El sandbox requiere acceso de administrador.");
            return;
        }
        if (args.Length != 1)
        {
            CommandManager.SendDefaultHelpText(this, messageOutput);
            return;
        }
        var result = MechanicsSandboxManager.Instance.Execute(character, args[0].ToLowerInvariant());
        messageOutput.SendMessage(HumanMessage(result));
    }

    internal static string HumanMessage(string result)
    {
        using var document = JsonDocument.Parse(result);
        var root = document.RootElement;
        var state = root.GetProperty("state").GetString();
        return state switch
        {
            "ready" => $"Escenario listo: {root.GetProperty("dummies").GetArrayLength()} muñecos de entrenamiento. Intento {root.GetProperty("attempt").GetInt32()}.",
            "initializing" or "resetting" => "Restableciendo el escenario de pruebas…",
            "clearing" => "Cerrando el escenario de pruebas…",
            "idle" => "No hay un escenario de pruebas activo.",
            "rejected" => "La acción no está disponible para este personaje o estado del escenario.",
            _ => "No se pudo preparar el escenario. Consulta el registro del sandbox."
        };
    }
}
