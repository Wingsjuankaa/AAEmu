using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Slaves;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Core.Managers;

public class RadarManager : Singleton<RadarManager>, IRadarManager
{
    private int RadarUpdateDelay { get => 1000; }
    private static object Lock { get; } = new();
    private Dictionary<uint, TelescopeRegistrationEntry> Registrations { get; set; } = [];
    private static int TransfersPerPacket { get => 10; }
    private static int FishPerPacket { get => 10; }
    private static int ShipsPerPacket { get => 10; }

    public void Initialize()
    {
        Registrations = [];
        TickManager.Instance.OnTick.Subscribe(RadarTick, TimeSpan.FromMilliseconds(RadarUpdateDelay), true);
    }

    public void RegisterForPublicTransport(Character player, float checkRange)
    {
        lock (Lock)
        {
            // If no entry, create one
            if (Registrations.TryGetValue(player.Id, out var entry))
            {
                entry.ShowPublicTransportRange = checkRange;
            }
            else
            {
                entry = new TelescopeRegistrationEntry
                {
                    Player = player,
                    ShowPublicTransportRange = checkRange,
                };
                Registrations.Add(player.Id, entry);
            }

            // If nothing set, delete
            if (entry.IsActive == false)
                Registrations.Remove(entry.Player.Id);
        }
    }

    public void RegisterForFishSchool(Character player, float checkRange)
    {
        lock (Lock)
        {
            // If no entry, create one
            if (Registrations.TryGetValue(player.Id, out var entry))
            {
                entry.ShowFishSchoolRange = checkRange;
            }
            else
            {
                entry = new TelescopeRegistrationEntry
                {
                    Player = player,
                    ShowFishSchoolRange = checkRange,
                };
                Registrations.Add(player.Id, entry);
            }

            // If nothing set, delete
            if (entry.IsActive == false)
                Registrations.Remove(entry.Player.Id);
        }
    }

    public void RegisterForShips(Character player, float checkRange)
    {
        lock (Lock)
        {
            // If no entry, create one
            if (Registrations.TryGetValue(player.Id, out var entry))
            {
                entry.ShowShipTelescopeRange = checkRange;
            }
            else
            {
                entry = new TelescopeRegistrationEntry
                {
                    Player = player,
                    ShowShipTelescopeRange = checkRange,
                };
                Registrations.Add(player.Id, entry);
            }

            // If nothing set, delete
            if (entry.IsActive == false)
                Registrations.Remove(entry.Player.Id);
        }
    }

    public int SetAllFishSchools(Character player, bool enabled)
    {
        lock (Lock)
        {
            if (!Registrations.TryGetValue(player.Id, out var entry))
            {
                entry = new TelescopeRegistrationEntry { Player = player };
                Registrations.Add(player.Id, entry);
            }
            entry.ShowAllFishSchools = enabled;
            var fish = SelectFishSchools(entry, FishSchoolManager.Instance.GetAllFishSchools());
            SendFishSchools(player, fish);
            if (!entry.IsActive)
                Registrations.Remove(player.Id);
            return fish.Count;
        }
    }

    internal static List<Doodad> SelectFishSchools(TelescopeRegistrationEntry entry, IEnumerable<Doodad> schools) =>
        schools.Where(fish => entry.EffectiveFishSchoolRange > 0 &&
            fish.Transform.WorldId == entry.Player.Transform.WorldId &&
            fish.Transform.InstanceId == entry.Player.Transform.InstanceId &&
            (entry.ShowAllFishSchools || RadarRangeRules.IsInRange(
                MathUtil.CalculateDistance(entry.Player, fish, true), entry.ShowFishSchoolRange))).ToList();

    internal static IEnumerable<SCSchoolOfFishDoodadsPacket> FishSchoolPackets(List<Doodad> schools)
    {
        // A final empty list clears pins after the last school disappears.
        if (schools.Count == 0)
            yield return new SCSchoolOfFishDoodadsPacket(true, []);
        for (var i = 0; i < schools.Count; i += FishPerPacket)
        {
            var count = Math.Min(FishPerPacket, schools.Count - i);
            yield return new SCSchoolOfFishDoodadsPacket(i + count == schools.Count, schools.GetRange(i, count).ToArray());
        }
    }

    private static void SendFishSchools(Character player, List<Doodad> schools)
    {
        foreach (var packet in FishSchoolPackets(schools))
            player.SendPacket(packet);
    }

    public void RadarTick(TimeSpan delta)
    {
        lock (Lock)
        {
            if (Registrations.Count <= 0)
                return;

            var allFish = FishSchoolManager.Instance.GetAllFishSchools();
            // TODO: Add Shipyards
            var allTransfers = new List<Transfer>();
            var allShips = new Dictionary<uint, List<Slave>>();
            foreach (var worldInstance in WorldManager.Instance.GetWorlds())
            {
                allTransfers.AddRange(worldInstance.TransferManager.GetTransfers());
                var shipList = worldInstance.SlaveManager.GetActiveSlavesByKinds(
                [
                    SlaveKind.Boat, SlaveKind.Fishboat, SlaveKind.Speedboat, SlaveKind.MerchantShip,
                    SlaveKind.BigSailingShip, SlaveKind.SmallSailingShip
                ]).ToList();
                allShips.TryAdd(worldInstance.Id, shipList);
            }

            foreach (var (_, entry) in Registrations)
            {
                if (entry.Player == null)
                    continue;

                // Check public Transportation
                if (entry.ShowPublicTransportRange > 0)
                {
                    var inRangeTransfers = new List<Transfer>();
                    foreach (var transfer in allTransfers)
                    {
                        // Ignore Carriage Boardings
                        if (transfer.TemplateId == 46)
                            continue;

                        if (transfer.Transform.WorldId != entry.Player.Transform.WorldId || transfer.Transform.InstanceId != entry.Player.Transform.InstanceId)
                            continue;

                        if (RadarRangeRules.IsInRange(
                                MathUtil.CalculateDistance(entry.Player, transfer, true),
                                entry.ShowPublicTransportRange))
                        {
                            inRangeTransfers.Add(transfer);
                        }
                    }

                    // Send Data
                    if (inRangeTransfers.Count > 0)
                    {
                        for (var i = 0; i < inRangeTransfers.Count; i += TransfersPerPacket)
                        {
                            var last = inRangeTransfers.Count - i <= TransfersPerPacket;
                            var temp = inRangeTransfers.GetRange(i, last ? inRangeTransfers.Count - i : TransfersPerPacket).ToArray();
                            entry.Player.SendPacket(new SCTransferTelescopeUnitsPacket(last, temp));
                        }
                    }
                }

                // GM access is explicit and revocable; normal buffs keep their range.
                var gmViewRevoked = entry.ShowAllFishSchools &&
                    CharacterManager.Instance.GetEffectiveAccessLevel(entry.Player) < 100;
                if (gmViewRevoked)
                    entry.ShowAllFishSchools = false;
                if (entry.EffectiveFishSchoolRange > 0 || gmViewRevoked)
                    SendFishSchools(entry.Player, SelectFishSchools(entry, allFish));

                // Check for All Ships
                if (entry.ShowShipTelescopeRange > 0)
                {
                    var inRangeShips = new List<Slave>();
                    foreach (var ship in allShips.GetValueOrDefault(entry.Player.Transform.InstanceId))
                    {
                        if (ship.Transform.WorldId != entry.Player.Transform.WorldId || ship.Transform.InstanceId != entry.Player.Transform.InstanceId)
                            continue;

                        if (RadarRangeRules.IsInRange(
                                MathUtil.CalculateDistance(entry.Player, ship, true),
                                entry.ShowShipTelescopeRange))
                        {
                            inRangeShips.Add(ship);
                        }
                    }

                    // Send Data
                    if (inRangeShips.Count > 0)
                    {
                        for (var i = 0; i < inRangeShips.Count; i += ShipsPerPacket)
                        {
                            var last = inRangeShips.Count - i <= ShipsPerPacket;
                            var temp = inRangeShips.GetRange(i, last ? inRangeShips.Count - i : ShipsPerPacket).ToArray();
                            entry.Player.SendPacket(new SCTelescopeUnitsPacket(last, temp));
                        }
                    }
                }

            } // for each player
        } // lock
    }

    public void UnRegister(Character player)
    {
        lock (Lock)
        {
            Registrations.Remove(player.Id);
        }
    }
}
