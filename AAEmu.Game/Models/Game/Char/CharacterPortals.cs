using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Packets.G2C;

using MySql.Data.MySqlClient;

using NLog;

namespace AAEmu.Game.Models.Game.Char;

public class CharacterPortals(Character owner, IPortalManager portalManager = null)
{
    private IPortalManager Manager => portalManager ?? PortalManager.Instance;
    private readonly object _visitSync = new();
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private Dictionary<uint, VisitedDistrict> VisitedDistricts { get; } = [];
    private readonly List<uint> _removedVisitedDistricts = [];
    private readonly List<uint> _removedPrivatePortals = [];

    public Dictionary<uint, Portal> PrivatePortals { get; set; } = [];
    public Dictionary<uint, Portal> DistrictPortals { get; set; } = [];
    public Character Owner { get; set; } = owner;

    public Portal GetPortalInfo(uint id)
    {
        if (DistrictPortals.TryGetValue(id, out var info))
            return info;
        // Client may pass either wire id (district) or the return-point id stored in Type.
        foreach (var portal in DistrictPortals.Values)
        {
            if (portal.Type == id)
                return portal;
        }

        return PrivatePortals.TryGetValue(id, out var privatePortal) ? privatePortal : null;
    }

    public void RemoveFromBookPortal(Portal portal, bool isPrivate)
    {
        lock (_visitSync)
            RemoveFromBookPortalCore(portal, isPrivate);
    }

    private void RemoveFromBookPortalCore(Portal portal, bool isPrivate)
    {
        if (isPrivate)
        {
            if (PrivatePortals.ContainsKey(portal.Id) && PrivatePortals.Remove(portal.Id))
            {
                _removedPrivatePortals.Add(portal.Id);
                //Owner.SendMessage("Recorded Portal deleted.");
            }
        }
        else
        {
            if (VisitedDistricts.ContainsKey(portal.SubZoneId) && VisitedDistricts.Remove(portal.SubZoneId))
            {
                _removedVisitedDistricts.Add(portal.SubZoneId);
                //Owner.SendMessage("Default Portal deleted.");
            }
        }
    }

    public void NotifySubZone(uint subZoneId)
    {
        lock (_visitSync)
            NotifySubZoneCore(subZoneId);
    }

    private void NotifySubZoneCore(uint subZoneId)
    {
        // Preserve physical-subzone discovery for legacy JSON locations, but never treat
        // a client subzone number as a native district id. The native area route is separate.
        if (subZoneId == 0 || subZoneId >= PortalVisitKey.SubZoneTag)
            return;
        var key = PortalVisitKey.ForSubZone(subZoneId);
        if (VisitedDistricts.ContainsKey(key) || VisitedDistricts.ContainsKey(subZoneId)) { return; }

        var portals = Manager.GetRecallBySubZoneId(subZoneId);
        if (portals == null || portals.Count == 0) { return; }

        var newVisitedDistrict = new VisitedDistrict
        {
            Id = VisitedSubZoneIdManager.Instance.GetNextId(), SubZone = key, Owner = Owner.Id
        };
        VisitedDistricts.Add(key, newVisitedDistrict);
        PopulateDistrictPortals();
        Send();

        Logger.Debug($"{Owner.Name} - subzone {subZoneId} added {portals.Count} return point(s) to district list");
        foreach (var portal in portals)
            Owner.SendDebugMessage($"{portal.Name}:{subZoneId} added to visited district list in the portal book");
    }

    public void NotifyDistrict(uint districtId)
    {
        lock (_visitSync)
            NotifyDistrictCore(districtId);
    }

    private void NotifyDistrictCore(uint districtId)
    {
        if (districtId == 0 || districtId >= PortalVisitKey.DistrictTag)
            return;
        var key = PortalVisitKey.ForDistrict(districtId);
        if (VisitedDistricts.ContainsKey(key) || ResolveNativeDistrictPortal(districtId) == null)
            return;
        if (!RecordNativeDistrict(districtId, VisitedSubZoneIdManager.Instance.GetNextId()))
            return;
        Send();
        Logger.Info("Teleport-book discovery char={0} district={1} returnPoint={2}",
            Owner.Name, districtId, DistrictPortals[districtId].Type);
    }

    private Portal ResolveNativeDistrictPortal(uint districtId)
    {
        var returnPointId = Manager.GetDistrictReturnPoint(districtId, Owner.Faction.Id);
        if (returnPointId == 0 && Owner.Faction.MotherId != Owner.Faction.Id)
            returnPointId = Manager.GetDistrictReturnPoint(districtId, Owner.Faction.MotherId);
        return Manager.GetRecallByDistrictId(districtId)?.FirstOrDefault(p => p.Id == returnPointId);
    }

    internal bool RecordNativeDistrict(uint districtId, uint recordId)
    {
        lock (_visitSync)
            return RecordNativeDistrictCore(districtId, recordId);
    }

    private bool RecordNativeDistrictCore(uint districtId, uint recordId)
    {
        var key = PortalVisitKey.ForDistrict(districtId);
        if (VisitedDistricts.ContainsKey(key) || ResolveNativeDistrictPortal(districtId) == null)
            return false;
        VisitedDistricts.Add(key, new VisitedDistrict { Id = recordId, SubZone = key, Owner = Owner.Id });
        PopulateDistrictPortals();
        return true;
    }

    public void AddPrivatePortal(float x, float y, float z, float zRot, uint zoneId, string name)
    {
        // TODO - Only working by command
        var newPortal = new Portal
        {
            Id = PrivateBookIdManager.Instance.GetNextId(),
            Name = name,
            X = x,
            Y = y,
            Z = z,
            ZoneId = zoneId,
            ZRot = zRot,
            Owner = Owner.Id
        };
        PrivatePortals.Add(newPortal.Id, newPortal);
        Owner.SendPacket(new SCCharacterPortalsPacket([newPortal]));
    }

    public bool ChangePrivatePortalName(uint id, string name)
    {
        if (PrivatePortals.TryGetValue(id, out var privatePortal))
        {
            privatePortal.Name = name;
            Owner.SendPacket(new SCPortalInfoSavedPacket(privatePortal));
            return true;
        }

        return false;
    }
    public void Send()
    {
        if (PrivatePortals.Count > 0)
        {
            var portals = new Portal[PrivatePortals.Count];
            PrivatePortals.Values.CopyTo(portals, 0);
            Owner.SendPacket(new SCCharacterPortalsPacket(portals));
        }

        if (DistrictPortals.Count > 0)
        {
            var portals = DistrictPortals.Values.ToArray();
            // Trailing field is the bound district id (client name returnDistrictId), not the return-point id.
            Owner.SendPacket(new SCCharacterReturnDistrictsPacket(portals, Owner.ReturnDistrictId));
        }
    }

    public void Load(MySqlConnection connection)
    {
        lock (_visitSync)
            LoadCore(connection);
    }

    private void LoadCore(MySqlConnection connection)
    {
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM portal_book_coords WHERE `owner` = @owner";
            command.Parameters.AddWithValue("@owner", Owner.Id);
            command.Prepare();
            using (var reader = command.ExecuteReader())
            {
                while (reader.Read())
                {
                    var template = new Portal
                    {
                        Id = reader.GetUInt32("id"),
                        Name = reader.GetString("name"),
                        X = reader.GetFloat("x"),
                        Y = reader.GetFloat("y"),
                        Z = reader.GetFloat("z"),
                        ZoneId = reader.GetUInt32("zone_id"),
                        ZRot = reader.GetFloat("z_rot"),
                        SubZoneId = reader.GetUInt32("sub_zone_id"),
                        Owner = reader.GetUInt32("owner")
                    };
                    PrivatePortals.Add(template.Id, template);
                }
            }
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT * FROM portal_visited_district WHERE `owner` = @owner";
            command.Parameters.AddWithValue("@owner", Owner.Id);
            command.Prepare();
            using (var reader = command.ExecuteReader())
            {
                while (reader.Read())
                {
                    var template = new VisitedDistrict
                    {
                        Id = reader.GetUInt32("id"),
                        SubZone = reader.GetUInt32("subzone"),
                        Owner = reader.GetUInt32("owner")
                    };
                    VisitedDistricts.Add(template.SubZone, template);
                }
            }
        }

        PopulateDistrictPortals();
    }

    public void Save(MySqlConnection connection, MySqlTransaction transaction)
    {
        lock (_visitSync)
            SaveCore(connection, transaction);
    }

    private void SaveCore(MySqlConnection connection, MySqlTransaction transaction)
    {
        if (_removedVisitedDistricts.Count > 0)
        {
            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = "DELETE FROM portal_visited_district WHERE owner = @owner AND subzone IN(" + string.Join(",", _removedVisitedDistricts) + ")";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                command.Prepare();
                command.ExecuteNonQuery();
                _removedVisitedDistricts.Clear();
            }
        }

        if (_removedPrivatePortals.Count > 0)
        {
            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = "DELETE FROM portal_book_coords WHERE owner = @owner AND id IN(" + string.Join(",", _removedPrivatePortals) + ")";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                command.Prepare();
                command.ExecuteNonQuery();
                _removedPrivatePortals.Clear();
            }
        }

        foreach (var (_, value) in PrivatePortals)
        {
            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = "REPLACE INTO portal_book_coords(`id`,`name`,`x`,`y`,`z`,`zone_id`,`z_rot`,`sub_zone_id`,`owner`) VALUES (@id, @name, @x, @y, @z, @zone_id, @z_rot, @sub_zone_id, @owner)";
                command.Parameters.AddWithValue("@id", value.Id);
                command.Parameters.AddWithValue("@name", value.Name);
                command.Parameters.AddWithValue("@x", value.X);
                command.Parameters.AddWithValue("@y", value.Y);
                command.Parameters.AddWithValue("@z", value.Z);
                command.Parameters.AddWithValue("@zone_id", value.ZoneId);
                command.Parameters.AddWithValue("@z_rot", value.ZRot);
                command.Parameters.AddWithValue("@sub_zone_id", value.SubZoneId);
                command.Parameters.AddWithValue("@owner", value.Owner);
                command.ExecuteNonQuery();
            }
        }

        foreach (var (_, value) in VisitedDistricts)
        {
            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = "REPLACE INTO portal_visited_district(`id`,`subzone`,`owner`) VALUES (@id, @subzone, @owner)";
                command.Parameters.AddWithValue("@id", value.Id);
                command.Parameters.AddWithValue("@subzone", value.SubZone);
                command.Parameters.AddWithValue("@owner", value.Owner);
                command.ExecuteNonQuery();
            }
        }
    }

    private void PopulateDistrictPortals()
    {
        DistrictPortals.Clear();
        if (VisitedDistricts.Count <= 0) { return; }

        foreach (var subZone in VisitedDistricts)
        {
            var nativeDistrict = PortalVisitKey.IsDistrict(subZone.Key)
                ? PortalVisitKey.DistrictId(subZone.Key) : 0;
            var portals = nativeDistrict != 0
                ? new[] { ResolveNativeDistrictPortal(nativeDistrict) }.Where(p => p != null).ToList()
                : Manager.GetRecallByVisitKey(subZone.Key);
            if (portals == null || portals.Count == 0) { continue; }

            foreach (var portal in portals)
            {
                // recalls.json Id == return_point_id. The client book entry uses district_id as
                // wire id and return_point_id as wire type (SC 0x089 capture: id=district, type=240).
                var districtId = nativeDistrict != 0 ? nativeDistrict
                    : Manager.GetDistrictIdByReturnPoint(portal.Id, Owner.Faction.Id);
                if (districtId == 0 && Owner.Faction.MotherId != Owner.Faction.Id)
                    districtId = Manager.GetDistrictIdByReturnPoint(portal.Id, Owner.Faction.MotherId);
                if (districtId == 0)
                    continue;

                var entry = new Portal
                {
                    Id = districtId,
                    Type = portal.Id,
                    Name = portal.Name,
                    X = portal.X,
                    Y = portal.Y,
                    Z = portal.Z,
                    ZoneId = portal.ZoneId,
                    ZRot = portal.ZRot,
                    SubZoneId = subZone.Key,
                    Owner = Owner.Id
                };
                DistrictPortals.TryAdd(entry.Id, entry);
            }
        }
    }
}
