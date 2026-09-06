using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items.Services;
using Microsoft.Data.Sqlite;
using System.Text.Json;

if (args.Length is < 1 or > 2) throw new ArgumentException("Read-only SQLite path required.");
using var connection = new SqliteConnection(new SqliteConnectionStringBuilder
    { DataSource = Path.GetFullPath(args[0]), Mode = SqliteOpenMode.ReadOnly }.ToString());
connection.Open();
var data = new EquipSlotReinforceGameData(); data.Load(connection); data.PostLoad();
var promotions = 0; var feeds = 0;
var state = new EquipSlotReinforceState();
foreach (var slot in data.Levels.Keys.Select(k => k.Slot).Distinct().Order())
{
    var levels = data.Levels.Values.Where(l => l.Slot == slot).OrderBy(l => l.Level).ToArray();
    foreach (var row in levels)
    {
        if (row.RequiredExperience == 0) continue;
        var candidates = data.Materials.Values.Where(m => m.Slot == slot && m.Level == row.Level).ToArray();
        if (candidates.Length == 0) throw new InvalidOperationException($"Unfeedable level {slot}/{row.Level}");
        foreach (var candidate in candidates)
        {
            var result = EquipSlotReinforceCalculator.AddExperience(data, state, slot, candidate.Id, false);
            if (result is null || result.Cost != candidate.Cost) throw new InvalidOperationException($"Rejected material {candidate.Id}");
            feeds++;
        }
        state = state.With(slot, new(row.Level, row.RequiredExperience));
        var up = EquipSlotReinforceCalculator.LevelUp(data, state, slot, _ => 0)
            ?? throw new InvalidOperationException($"Promotion rejected {slot}/{row.Level}");
        state = up.State; promotions++;
        if (up.ChangedEffect is { } key && EquipSlotReinforceCalculator.ChangeEffect(data, state, slot,
                key.Level, maximum => maximum - 1) is null) throw new InvalidOperationException($"Reroll rejected {key}");
    }
}
if (state.Effects.Count != data.Milestones.Count) throw new InvalidOperationException("Missing maximum-level effects.");
Console.WriteLine(JsonSerializer.Serialize(new { data.MinimumLevel, data.RerollItem,
    Levels=data.Levels.Count, Materials=data.Materials.Count, Modifiers=data.Modifiers.Count,
    data.IgnoredModifierCount, feeds, promotions, Effects=state.Effects.Count,
    MaxBonuses=EquipSlotReinforceCalculator.GetBonuses(data,state).Count }));

if (args.Length == 2 && args[1] == "--mysql") IpnyaPersistenceSmoke.Run(data, state);
