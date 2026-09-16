// The production MySQL repository runs against connection-local TEMPORARY tables.
// Real accounts, characters, permissions and inventories are never mutated.
// Credentials arrive through stdin, never command-line arguments or output.
using System.Reflection;
using System.Text.Json;
using AAEmu.Commons.Models;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Models.Game.PrivateAlpha;
using MySql.Data.MySqlClient;

MySQL.SetConfiguration(JsonSerializer.Deserialize<MySqlConnectionSettings>(Console.In.ReadToEnd())!);
using var db = MySQL.CreateConnection();
var repository = typeof(AlphaService).Assembly.GetType("AAEmu.Game.Models.Game.PrivateAlpha.AlphaRepository")!;
var check = repository.GetMethod("HasAccess", BindingFlags.NonPublic | BindingFlags.Static,
    [typeof(MySqlConnection), typeof(uint)])!;
var assertions = 0;
void Expect(uint id, bool expected)
{
    var actual = (bool)check.Invoke(null, [db, id])!;
    if (actual != expected) throw new InvalidOperationException($"Permission mismatch for fixture {id}");
    assertions++;
}
void Execute(string sql)
{
    using var command = db.CreateCommand();
    command.CommandText = sql;
    command.ExecuteNonQuery();
}

Execute("""
    CREATE TEMPORARY TABLE characters (id INT UNSIGNED PRIMARY KEY, account_id INT UNSIGNED, deleted INT);
    CREATE TEMPORARY TABLE private_alpha_access (character_id INT UNSIGNED PRIMARY KEY);
    CREATE TEMPORARY TABLE private_alpha_account_access (account_id INT UNSIGNED PRIMARY KEY);
    INSERT INTO characters VALUES (101,5,0),(102,5,0),(103,9,0),(104,5,1);
    INSERT INTO private_alpha_account_access VALUES (5);
    """);
Expect(101, true);
Expect(102, true);
Expect(103, false);
Expect(104, false);
Expect(105, false);
Execute("INSERT INTO characters VALUES (105,5,0)");
Expect(105, true);
Execute("INSERT INTO private_alpha_access VALUES (102),(103); DELETE FROM private_alpha_account_access WHERE account_id=5");
Expect(101, false);
Expect(105, false);
Expect(102, true);
Expect(103, true);
Execute("INSERT INTO private_alpha_account_access VALUES (5); DELETE FROM private_alpha_access WHERE character_id=102");
Expect(102, true);
Execute("UPDATE characters SET account_id=9 WHERE id=102");
Expect(102, false);
Console.WriteLine(JsonSerializer.Serialize(new { state = "passed", assertions,
    engine = "MySQL", repository = "production", existing_and_future_characters = true,
    account_revocation = true, independent_permissions_preserved = true,
    unrelated_and_deleted_denied = true, production_mutations = 0 }));
