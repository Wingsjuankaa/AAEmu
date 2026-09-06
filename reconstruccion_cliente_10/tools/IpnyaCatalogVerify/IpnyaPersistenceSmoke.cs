using System.Reflection;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Items.Containers;
using AAEmu.Game.Models.Game.Formulas;
using Jace;
using AAEmu.Commons.Models;
using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using MySql.Data.MySqlClient;
using Newtonsoft.Json.Linq;

internal static class IpnyaPersistenceSmoke
{
    internal static void Run(EquipSlotReinforceGameData data, EquipSlotReinforceState maximum)
    {
        // Explicit opt-in. Credentials stay in the existing local configuration and never enter logs.
        var config=JObject.Parse(File.ReadAllText(".server_files/AAEmu.Game/Config.json"));
        var settings=config["Connections"]!["MySQLProvider"]!.ToObject<MySqlConnectionSettings>()!;
        settings.Host="127.0.0.1"; settings.Port=24306;
        MySQL.SetConfiguration(settings);
        using var admin=MySQL.CreateConnection();
        var schema="ipnya_verify_"+Guid.NewGuid().ToString("N");
        using var command=admin.CreateCommand();
        command.CommandText=$"CREATE DATABASE `{schema}`";command.ExecuteNonQuery();
        try
        {
            settings.Database=schema;MySQL.SetConfiguration(settings);
            using var db=MySQL.CreateConnection();
            Exec(db,"CREATE TABLE characters (id INT UNSIGNED PRIMARY KEY, money BIGINT NOT NULL, aa_point BIGINT NOT NULL) ENGINE=InnoDB");
            Exec(db,"CREATE TABLE items LIKE aaemu_game.items");
            Exec(db,File.ReadAllText("SQL/updates/2026-09-06_aaemu_game_equip_slot_reinforce.sql"));
            Exec(db,"INSERT INTO characters VALUES (1,100,50)");
            typeof(Singleton<EquipSlotReinforceGameData>).GetField("s_instance",BindingFlags.Static|BindingFlags.NonPublic)!.SetValue(null,data);
            var owner=new Character(null) { Id=1 };
            var service=new CharacterEquipSlotReinforce(owner);
            var persist=typeof(CharacterEquipSlotReinforce).GetMethod("Persist",BindingFlags.Instance|BindingFlags.NonPublic)!;
            var item=new Item(999,new ItemTemplate { Id=51594,MaxCount=100 },10) { OwnerId=1,SlotType=SlotType.Inventory,Slot=0,CreateTime=DateTime.UtcNow };
            var selected=new List<(Item Item,int Amount)> { (item,2) };
            var plan=new EquipSlotReinforcePlan(maximum,0,[(51594u,2)],25,false);
            persist.Invoke(service,[plan,selected,75L,50L]);
            Require(Scalar(db,"SELECT count FROM items WHERE id=999")==8,"Unsaved stack was not persisted with post-payment count");
            Require(Scalar(db,"SELECT money FROM characters WHERE id=1")==75,"Wallet did not commit");
            var loaded=new CharacterEquipSlotReinforce(owner);loaded.Load(db);
            owner.EquipSlotReinforce=loaded;
            var features=new FeatureSet();features.Set(Feature.equipSlotEnchantment,true);
            typeof(FeaturesManager).GetProperty(nameof(FeaturesManager.Fsets))!.SetValue(null,features);
            var engine=new CalculationEngine(new JaceOptions { CultureInfo=System.Globalization.CultureInfo.InvariantCulture,CaseSensitive=true });engine.AddFunction("if_negative",(double a,double b,double c)=>a<0?b:c);
            typeof(FormulaManager).GetProperty(nameof(FormulaManager.CalculationEngine))!.SetValue(FormulaManager.Instance,engine);
            using(var sqlite=new Microsoft.Data.Sqlite.SqliteConnection("Data Source=.server_files/AAEmu.Game/Data/compact.sqlite3;Mode=ReadOnly"))
            {
                sqlite.Open();using var formulaQuery=sqlite.CreateCommand();formulaQuery.CommandText="SELECT formula FROM formulas WHERE id=69";
                var formula=new Formula { Id=69,TextFormula=(string)formulaQuery.ExecuteScalar()! };
                Require(formula.Prepare(),"Formula69 failed compilation");
                typeof(FormulaManager).GetField("_formulas",BindingFlags.Instance|BindingFlags.NonPublic)!.SetValue(FormulaManager.Instance,new Dictionary<uint,Formula> { [69]=formula });
            }
            foreach(var itemLevel in new[]{20,40,55})
            {
                var gain=data.Levels[(0,maximum.Get(0).Level)].GainItemLevel;
                var expected=itemLevel<40?gain*(286-itemLevel*0.65)/(itemLevel*3.7+210):gain*(450-itemLevel)/(itemLevel*8.7+190);
                Require(Math.Abs(loaded.GetItemLevelGain(0,itemLevel)-expected)<1e-8,"Formula69 branch mismatch");
            }
            var equipment=new ItemContainer(0,SlotType.Equipment,false,owner);
            var armor=new EquipItem { Template=new ItemTemplate { Level=55 },SlotType=SlotType.Equipment,Slot=0 };
            armor._holdingContainer=equipment;
            Require(armor.EffectiveStatLevel>55,"Equipped slot did not gain combat item level");
            armor.SlotType=SlotType.Inventory;Require(armor.EffectiveStatLevel==55,"Bag item received slot bonus");
            armor.SlotType=SlotType.Equipment;features.Set(Feature.equipSlotEnchantment,false);
            Require(armor.EffectiveStatLevel==55 && loaded.Bonuses.Count==0,"Disabled feature retained bonuses");
            features.Set(Feature.equipSlotEnchantment,true);
            Require(loaded.Bonuses.Count==44,"Milestones and cumulative bundles not applied");
            Require(loaded.Snapshot.Slots.Count==16 && loaded.Snapshot.Effects.Count==38,"Relog state lost slots or effects");
            foreach(var (key,value) in maximum.Effects) Require(loaded.Snapshot.Effects[key]==value,"Relog modifier mismatch");
            // Fail after both inventory and wallet SQL have run; DB constraints force transaction rollback.
            var invalid=plan with { State=maximum.With(0,new(1,-1)) };
            var rejected=false;
            try { persist.Invoke(service,[invalid,selected,1L,1L]); }
            catch(TargetInvocationException e) when(e.InnerException is MySqlException) { rejected=true; }
            Require(rejected,"Injected SQL constraint failure was not rejected");
            Require(Scalar(db,"SELECT money FROM characters WHERE id=1")==75 && Scalar(db,"SELECT count FROM items WHERE id=999")==8,"Failed commit mutated payment");
            loaded.Load(db);Require(loaded.Snapshot.Get(0).Level==maximum.Get(0).Level,"Failed commit mutated progression");
            // A fully consumed stack is deleted in the same transaction as the durable result.
            selected[0]=(item,10);persist.Invoke(service,[plan,selected,75L,50L]);
            Require(Scalar(db,"SELECT COUNT(*) FROM items WHERE id=999")==0,"Full consumption retained item");
            Exec(db,"DELETE FROM characters WHERE id=1");rejected=false;
            try { persist.Invoke(service,[plan,selected,75L,50L]); }
            catch(TargetInvocationException e) when(e.InnerException is InvalidOperationException) { rejected=true; }
            Require(rejected,"Missing owner accepted payment");
            Console.WriteLine("MYSQL/STATS PASS: formula69 both branches, equipped/bag/feature-off separation, 44 bonuses; actual Persist + repository; unsaved stack, wallet, 16 slots/38 effects reload, post-payment SQL failure rollback, full deletion, missing owner rejection.");
        }
        finally
        {
            command.CommandText=$"DROP DATABASE `{schema}`";command.ExecuteNonQuery();
            Console.WriteLine("Scratch database removed; live character and item rows untouched.");
        }
    }
    private static void Exec(MySqlConnection db,string sql) { using var c=db.CreateCommand();c.CommandText=sql;c.ExecuteNonQuery(); }
    private static long Scalar(MySqlConnection db,string sql) { using var c=db.CreateCommand();c.CommandText=sql;return Convert.ToInt64(c.ExecuteScalar()); }
    private static void Require(bool condition,string message) { if(!condition) throw new InvalidOperationException(message); }
}
