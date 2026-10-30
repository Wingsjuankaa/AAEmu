using System.Security.Cryptography;
using System.Text.Json;
using System.Xml;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.ClientData;
using AAEmu.Game.Models.Game.World;
using Microsoft.Data.Sqlite;

if (args.Length != 3)
    throw new ArgumentException("Usage: AA10SandboxZoneVerify <assets-root> <full.sqlite3> <compact.sqlite3>");
var assets = Path.GetFullPath(args[0]);
if (!assets.StartsWith("E:\\AAEmu\\rama_10\\artifacts\\", StringComparison.OrdinalIgnoreCase))
    throw new ArgumentException("Only the offline artifacts on E may be verified");
var doc = new XmlDocument { XmlResolver = null };
doc.Load(Path.Combine(assets, "game/worlds/main_world/world.xml"));
var template = new WorldTemplate { Id = 0 };
template.XmlWorld.ReadNode(doc.DocumentElement!, template);
if (template.Name != "main_world" || template.CellX != 2 || template.CellY != 2 ||
    template.XmlWorld.IsInstance != 0 || template.ZoneKeys.Count != 1 || template.ZoneKeys[0] != 411)
    throw new InvalidDataException("The real World XML consumer did not create the isolated Zone411 layout");
var manager = new WorldManager(null!, null!, null!, null!, null!);
var positions = new (string Name, float X, float Y)[] {
    ("player",575,506), ("dummy5",575,511), ("dummy10-left",573,516),
    ("dummy10-center",575,516), ("dummy10-right",577,516),
    ("specializations",569,503), ("bank",573,503), ("weapons",577,503), ("armor",581,503)};
foreach (var point in positions)
    if (manager.GetZoneId(template, point.X, point.Y) != 411)
        throw new InvalidDataException($"Position {point.Name} does not belong to Zone411");

var heightmap = new Hmap();
using (var binary = new BinaryReader(File.OpenRead(Path.Combine(assets, "game/worlds/main_world/cells/000_000/client/terrain/heightmap.dat"))))
    if (heightmap.Read(binary, false) < 0)
        throw new InvalidDataException("The actual server Hmap parser rejected the copied retail heightmap");
var leaves = heightmap.Nodes.Where(node => node.pHMData.Length > 0)
    .OrderBy(node => node.BoxHeightmap.Min.X).ThenBy(node => node.BoxHeightmap.Min.Y).ToArray();
if (leaves.Length != 256)
    throw new InvalidDataException($"Unexpected heightmap leaf count {leaves.Length}");
var heights = positions.Select(point => new {
    point.Name, point.X, point.Y,
    TerrainHeight = leaves[(int)(point.X / 64) * 16 + (int)(point.Y / 64)]
        .GetHeight((ushort)((int)(point.X % 64) / 2), (ushort)((int)(point.Y % 64) / 2))
}).ToArray();
if (heights.Any(point => !float.IsFinite(point.TerrainHeight)))
    throw new InvalidDataException("Invalid decoded terrain height");

var catalogs = new List<object>();
foreach (var input in args.Skip(1))
{
    var path = Path.GetFullPath(input);
    if (!path.StartsWith("E:\\AAEmu\\rama_10\\artifacts\\", StringComparison.OrdinalIgnoreCase))
        throw new ArgumentException("Only offline derived catalogs may be verified");
    using var sql = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = path, Mode = SqliteOpenMode.ReadOnly }.ToString());
    sql.Open();
    using var command = sql.CreateCommand();
    command.CommandText = "SELECT z.name,z.group_id,z.closed,g.hide_world_pos,g.target_id,g.buff_id FROM zones z JOIN zone_groups g ON g.id=z.group_id WHERE z.zone_key=411";
    using var row = command.ExecuteReader();
    if (!row.Read() || row.GetString(0) != "aa10_sandbox_lab" || row.GetInt32(1) != 159 ||
        row.GetString(2) != "f" || row.GetString(3) != "t" || row.GetInt32(4) != 1 ||
        !row.IsDBNull(5) && row.GetInt32(5) != 0 || row.Read())
        throw new InvalidDataException("The actual SQLite reader did not resolve the private hidden zone");
    catalogs.Add(new { Path = path, Bytes = new FileInfo(path).Length });
}
Console.WriteLine(JsonSerializer.Serialize(new { Success = true, Consumer = "AAEmu.Game real XmlWorld/GetZoneId/Hmap and Microsoft.Data.Sqlite readers",
    World = template.Name, WorldId = 0, Zone = 411, CellX = template.CellX, CellY = template.CellY,
    HeightmapVersion = heightmap.Version, HeightmapNodes = heightmap.Nodes.Count, HeightmapLeaves = leaves.Length,
    Heights = heights, Catalogs = catalogs, NativeCollisionAcceptance = "requires Zone411 and client observation" }));
