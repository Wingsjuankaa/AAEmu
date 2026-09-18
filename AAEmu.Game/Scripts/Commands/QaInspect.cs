using System;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.Game.Scripts.Commands;

/// <summary>Read-only observations for reproducing client/server discrepancies.</summary>
public class QaInspect : ICommand
{
    public string[] CommandNames { get; set; } = ["qainspect"];
    public void OnLoad() => CommandManager.Instance.Register(CommandNames, this);
    public string GetCommandLineHelp() => "self | target | gear";
    public string GetCommandHelpText() => "Lee HP, buffs y estado del plot, o desglosa la puntuación de equipo. No modifica el estado.";
    public void Execute(Character character, string[] args, IMessageOutput output)
    {
        if (args.Length != 1 || args[0] is not ("self" or "target" or "gear"))
        {
            CommandManager.SendDefaultHelpText(this, output);
            return;
        }
        if (args[0] == "gear")
        {
            foreach (var item in character.Inventory.Equipment.Items.ToArray())
                if (item is EquipItem equip)
                    output.SendMessage(JsonSerializer.Serialize(new {
                        item.Id, item.TemplateId, item.Slot, equip.Grade, equip.ElementLevel,
                        Level = item.Template.Level, Sockets = equip.NativeSocketItemIds,
                        Score = GearScoreCalculator.EvaluateItem(item)
                    }));
            output.SendMessage(JsonSerializer.Serialize(new { Cached = character.GearScore, Recalculated = GearScoreCalculator.Evaluate(character) }));
            return;
        }
        var unit = args[0] == "self" ? character : character.CurrentTarget as Unit;
        if (unit == null)
        {
            CommandManager.SendErrorText(this, output, "Selecciona una unidad.");
            return;
        }
        var good = new List<Buff>();
        var bad = new List<Buff>();
        var hidden = new List<Buff>();
        unit.Buffs.GetAllBuffs(good, bad, hidden, true);
        output.SendMessage(JsonSerializer.Serialize(new {
            Utc = DateTime.UtcNow, unit.ObjId, unit.Hp, unit.MaxHp, unit.Mp, unit.MaxMp,
            ActivePlot = unit.ActivePlotState != null, unit.IsInBattle,
            Buffs = good.Concat(bad).Concat(hidden).Select(b => b.Template.Id).OrderBy(id => id).ToArray()
        }));
    }
}
