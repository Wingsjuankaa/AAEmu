using System.Globalization;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;
using NLog;

namespace AAEmu.Game.Scripts.Commands;

public class Ezi : ICommand
{
    private static readonly Logger Logger = LogManager.GetCurrentClassLogger();
    public string[] CommandNames { get; set; } = ["ezi"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "<segundos> [radioMetros]";
    public string GetCommandHelpText() =>
        "Crea una zona de Ezi en tu posición para reparar y personalizar barcos. " +
        "Duración: 1–86400 segundos. Radio: 5–500 m (50 por defecto). /ezi 0 retira tu zona de esta instancia.";

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        if (args.Length is < 1 or > 2 ||
            !int.TryParse(args[0], NumberStyles.None, CultureInfo.InvariantCulture, out var seconds) ||
            seconds is < 0 or > TemporaryEziAreaManager.MaxSeconds)
        {
            CommandManager.SendDefaultHelpText(this, messageOutput);
            return;
        }
        var radius = TemporaryEziAreaManager.DefaultRadius;
        if ((seconds == 0 && args.Length != 1) || (args.Length == 2 &&
            (!float.TryParse(args[1], NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out radius) ||
             !float.IsFinite(radius) || radius is < 5 or > 500)))
        {
            CommandManager.SendDefaultHelpText(this, messageOutput);
            return;
        }
        var world = character.ParentWorld;
        if (world == null)
        {
            messageOutput.SendMessage("No se pudo localizar la instancia del personaje.");
            return;
        }
        if (seconds == 0)
        {
            var removed = world.TemporaryEziAreas.Remove(character.Id);
            messageOutput.SendMessage(removed ? "Zona de Ezi retirada." : "No tienes una zona de Ezi activa en esta instancia.");
            Logger.Info("TemporaryEzi REMOVE char={0} instance={1} removed={2}", character.Id, world.Id, removed);
            return;
        }
        if (SkillManager.Instance.GetBuffTemplate(TemporaryEziAreaManager.EziBuffId) == null ||
            SkillManager.Instance.GetBuffTemplate(TemporaryEziAreaManager.MooredBuffId) == null)
        {
            messageOutput.SendMessage("No se pudo crear la zona: faltan los efectos de Ezi en el catálogo.");
            return;
        }
        var position = character.Transform.World.Position;
        world.TemporaryEziAreas.Place(character.Id, position, seconds, radius, DateTime.UtcNow);
        messageOutput.SendMessage($"Zona de Ezi creada durante {seconds} segundos, con radio de {radius} m. " +
            "Queda fija en esta posición y reemplaza tu zona anterior de esta instancia.");
        Logger.Info("TemporaryEzi PLACE char={0} instance={1} pos={2} seconds={3} radius={4}",
            character.Id, world.Id, position, seconds, radius);
    }
}
