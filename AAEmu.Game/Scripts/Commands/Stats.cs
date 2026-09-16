using System.Globalization;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.Game.Scripts.Commands;

public class Stats : ICommand
{
    public string[] CommandNames { get; set; } = ["stats", "gmstats"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "show | list | set <stat> <bonus> | damage <percent> | reset [stat]";
    public string GetCommandHelpText() =>
        "Bonificaciones GM temporales sobre ti. set reemplaza la bonificacion, no el total. " +
        "damage 900 agrega +900% al modificador de ataques cuerpo a cuerpo, a distancia y magia. " +
        "reset restaura; relog tambien las elimina. Ventana C calculada por cliente: consulta show.";

    public void Execute(Character character, string[] args, IMessageOutput output)
    {
        if (args.Length == 0 || (args.Length == 1 && args[0].Equals("show", StringComparison.OrdinalIgnoreCase)))
        {
            CommandManager.SendNormalText(this, output, "Bonificaciones de servidor; no persistentes. La ventana C puede diferir.");
            foreach (var stat in GmStatBonuses.Definitions)
                CommandManager.SendNormalText(this, output,
                    $"{stat.Name}: bonus={character.GmStats.Get(stat.Attribute)}, atributo servidor={character.GetAttribute(stat.Attribute)}");
            return;
        }
        if (args.Length == 1 && args[0].Equals("list", StringComparison.OrdinalIgnoreCase))
        {
            foreach (var stat in GmStatBonuses.Definitions)
                CommandManager.SendNormalText(this, output, $"{stat.Name}: 0..{stat.Maximum} " +
                    (stat.Name.EndsWith("_damage", StringComparison.Ordinal) ? "% adicional" : "puntos adicionales"));
            return;
        }

        var action = args[0].ToLowerInvariant();
        var name = "";
        var value = 0;
        var resetAll = action == "reset" && args.Length == 1;
        if (action == "reset" && args.Length == 2)
            name = args[1];
        else if (action == "set" && args.Length == 3 &&
                 int.TryParse(args[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            name = args[1];
        else if (action == "damage" && args.Length == 2 &&
                 int.TryParse(args[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            name = "damage";
        else if (!resetAll)
        {
            CommandManager.SendDefaultHelpText(this, output);
            return;
        }

        // Validate before calculating/mutating vitals; malformed requests leave the session intact.
        if (resetAll)
            character.GmStats.Clear();
        else if (!character.GmStats.Set(name, value))
        {
            CommandManager.SendErrorText(this, output, "Estadistica o valor invalido. Consulta /stats list; usa 0 para quitar una bonificacion.");
            return;
        }

        // Maxima may shrink on reset or when replacing stamina/intelligence. Do not grant healing.
        var hp = Math.Min(character.Hp, character.MaxHp);
        var mp = Math.Min(character.Mp, character.MaxMp);
        if (hp != character.Hp || mp != character.Mp)
        {
            character.Hp = hp;
            character.Mp = mp;
            character.BroadcastPacket(new SCUnitPointsPacket(character.ObjId, hp, mp), true);
            if (WorldIntegration.ZoneAuthority)
                WorldIntegration.RelayUnitPointsToZone?.Invoke(character.ObjId, hp, mp);
        }
        CommandManager.SendNormalText(this, output, resetAll
            ? "Bonificaciones GM eliminadas; equipo y buffs conservados."
            : $"{name}: bonificacion GM = {value}. Reemplazada, no acumulada. /stats reset para restaurar.");
    }
}
