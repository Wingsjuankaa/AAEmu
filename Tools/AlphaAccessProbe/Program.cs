// Read-only: exercise the production entitlement check without constructing inventory.
// Connection settings arrive via stdin, never command-line arguments or output.
using System.Text.Json;
using AAEmu.Commons.Models;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.PrivateAlpha;

if (args.Length != 1 || !uint.TryParse(args[0], out var character)) return 2;
MySQL.SetConfiguration(JsonSerializer.Deserialize<MySqlConnectionSettings>(Console.In.ReadToEnd())!);
AppConfiguration.Instance.PrivateAlpha.Enabled = true;
if (!AlphaService.IsAuthorized(character)) throw new InvalidOperationException("Expected authorized fixture");
using var db = MySQL.CreateConnection();
using var cmd = db.CreateCommand();
cmd.CommandText = "SELECT id FROM characters WHERE deleted=0 AND id NOT IN (SELECT character_id FROM private_alpha_access) LIMIT 1";
var other = Convert.ToUInt32(cmd.ExecuteScalar() ?? throw new InvalidOperationException("No unauthorized fixture"));
if (AlphaService.IsAuthorized(other)) throw new InvalidOperationException("Unauthorized character accepted");
AppConfiguration.Instance.PrivateAlpha.Enabled = false;
if (AlphaService.IsAuthorized(character)) throw new InvalidOperationException("Disabled feature accepted");
Console.WriteLine(JsonSerializer.Serialize(new { state="passed", character_id=character, authorization_without_inventory=true,
    unauthorized_denied=true, disabled_denied=true, database_mutations=0 }));
return 0;
