using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.PrivateAlpha;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.Game.Scripts.Commands;

public sealed class AlphaAccess : ICommand
{
    public string[] CommandNames { get; set; } = ["alphaaccess"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "<grant|revoke> <personaje online>";
    public string GetCommandHelpText() => "Concede acceso a la alpha con su llave ligada o revoca el acceso inmediatamente.";
    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        // Explicit check also protects direct invocation if the generic access config is loosened.
        if (CharacterManager.Instance.GetEffectiveAccessLevel(character) < 100)
        { messageOutput.SendMessage("Sólo un administrador puede autorizar la alpha."); return; }
        if (args.Length != 2 || args[0] is not ("grant" or "revoke"))
        { CommandManager.SendDefaultHelpText(this, messageOutput); return; }
        var target = WorldManager.Instance.GetCharacter(args[1]);
        if (target?.IsOnline != true) { messageOutput.SendMessage("El personaje debe estar conectado."); return; }
        messageOutput.SendMessage(AlphaService.SetAccess(target, character.Id, args[0] == "grant")
            ? $"Alpha: {args[0]} aplicado a {target.Name}." : "No se pudo conceder acceso: revisa activación y espacio en el bolso.");
    }
}
