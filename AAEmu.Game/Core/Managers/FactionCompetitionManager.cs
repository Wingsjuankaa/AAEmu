using AAEmu.Commons.Utils;
using AAEmu.Commons.Utils.DB;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.FactionCompetition;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Zones;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Utils.DB;
using MySql.Data.MySqlClient;
using Microsoft.Data.Sqlite;
using NLog;
using WorldIntegration = AAEmu.Game.WorldIntegration;

namespace AAEmu.Game.Core.Managers;

/// <summary>
/// AA10 r575 faction-competition and conquest-result authority. Static rules come from the
/// decrypted client SQLite; only live scores/times are persisted in MySQL.
/// </summary>
public sealed class FactionCompetitionManager(IWorldManager worldManager, IZoneManager zoneManager)
    : Singleton<FactionCompetitionManager>, IFactionCompetitionManager
{
    private static Logger Logger { get; } = LogManager.GetCurrentClassLogger();
    private readonly object _sync = new();
    private readonly Dictionary<ushort, FactionCompetitionState> _competitions = [];
    private readonly Dictionary<ushort, FactionCompetitionState> _conquests = [];
    private readonly Dictionary<uint, ushort> _towerToConquestZone = new() { [126] = 78 };
    private readonly Dictionary<uint, ushort> _towerToCompetitionZone = [];
    private readonly Dictionary<uint, HashSet<uint>> _competitionNpcs = [];
    private readonly Dictionary<uint, HashSet<uint>> _competitionQuests = [];
    private readonly Dictionary<(uint CompetitionId, int FactionId), uint> _winnerTowerDefs = [];

    public void Load()
    {
        lock (_sync)
        {
            _competitions.Clear();
            _conquests.Clear();
            _towerToCompetitionZone.Clear();
            _competitionNpcs.Clear();
            _competitionQuests.Clear();
            _winnerTowerDefs.Clear();

            using var connection = SQLite.CreateConnection();
            LoadCompetitions(connection);
            LoadRelations(connection);
            LoadConquests(connection);
            LoadPersistentStates();
            ReconcileLoadedZoneStates();

            WorldIntegration.OnZoneConflictStateChanged = OnZoneStateChanged;
            WorldIntegration.OnTowerDefStarted = OnTowerDefStarted;
            WorldIntegration.OnTowerDefEnded = OnTowerDefEnded;
            WorldIntegration.OnFactionCompetitionPcKill = OnPcKill;
            WorldIntegration.OnFactionCompetitionNpcKill = OnNpcKill;
            WorldIntegration.OnFactionCompetitionQuestCompleted = OnQuestCompleted;
            WorldIntegration.GiveFactionCompetitionPoint = GiveSpecialPoint;
            WorldIntegration.SyncFactionCompetitionToCharacter = SyncToCharacter;
        }

        Logger.Info("Loaded {0} faction competitions and {1} conquest result authorities",
            _competitions.Count, _conquests.Count);
    }

    private void LoadCompetitions(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = @"
SELECT fc.*, cz.zone_group_id, cz.faction_competition_zone_state_kind_id
FROM faction_competitions fc
JOIN conflict_zones cz ON cz.faction_competition_kind_id = fc.id
ORDER BY cz.zone_group_id";
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
        {
            var zoneGroupId = reader.GetUInt16("zone_group_id");
            var template = new FactionCompetitionTemplate
            {
                Id = reader.GetUInt32("id"),
                ZoneGroupId = zoneGroupId,
                Mode = reader.GetString("detail_type") == "CompetitionPve"
                    ? FactionCompetitionMode.Pve
                    : FactionCompetitionMode.Pvp,
                PcKillPoint = reader.GetInt32("point_pc_kill_value"),
                NpcKillPoint = reader.GetInt32("point_npc_kill_value"),
                QuestCompletePoint = reader.GetInt32("point_quest_complete_value"),
                RequiredPoint = reader.GetUInt32("req_point"),
                ResetKind = (FactionCompetitionResetKind)reader.GetByte("point_reset_id"),
                ForceChangeState = reader.GetBoolean("force_change_state"),
                ForceStopTowerDefId = reader.GetUInt32("force_stop_tower_def_id", 0),
                ZoneStateKind = reader.GetByte("faction_competition_zone_state_kind_id")
            };
            var state = new FactionCompetitionState(template);
            state.Restore(false, DateTime.MinValue, DateTime.MinValue,
                template.Mode == FactionCompetitionMode.Pve
                    ? [new FactionCompetitionPoint(4, 0), new FactionCompetitionPoint(5, 0)]
                    : [new FactionCompetitionPoint(1, 0), new FactionCompetitionPoint(2, 0), new FactionCompetitionPoint(3, 0)]);
            _competitions[zoneGroupId] = state;
            if (template.ForceStopTowerDefId != 0)
                _towerToCompetitionZone[template.ForceStopTowerDefId] = zoneGroupId;
        }
    }

    private void LoadRelations(SqliteConnection connection)
    {
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT faction_competition_id, npc_id FROM faction_competition_npc_infos";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
            {
                var competitionId = reader.GetUInt32("faction_competition_id");
                if (!_competitionNpcs.TryGetValue(competitionId, out var set))
                    _competitionNpcs[competitionId] = set = [];
                set.Add(reader.GetUInt32("npc_id"));
            }
        }
        foreach (var (competitionId, contextId) in ReadCompetitionQuestRelations(connection))
        {
            if (!_competitionQuests.TryGetValue(competitionId, out var set))
                _competitionQuests[competitionId] = set = [];
            set.Add(contextId);
        }
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT faction_competition_id, location_id, tower_def_id FROM competition_tower_defs";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                _winnerTowerDefs[(reader.GetUInt32("faction_competition_id"), reader.GetInt32("location_id"))] =
                    reader.GetUInt32("tower_def_id");
        }
    }

    internal static IReadOnlyList<(uint CompetitionId, uint ContextId)> ReadCompetitionQuestRelations(
        SqliteConnection connection)
    {
        var result = new List<(uint CompetitionId, uint ContextId)>();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT faction_competition_id, context_id FROM faction_competition_quest_infos";
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
            result.Add((reader.GetUInt32("faction_competition_id"), reader.GetUInt32("context_id")));
        return result;
    }

    private void LoadConquests(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT DISTINCT zone_group_id FROM quest_act_obj_conquest_wars ORDER BY zone_group_id";
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
        {
            var zoneGroupId = reader.GetUInt16("zone_group_id");
            if (zoneGroupId != 78) // zone 20 is resolved by its authored faction competition winner
                continue;
            var template = new FactionCompetitionTemplate
            {
                Id = zoneGroupId,
                ZoneGroupId = zoneGroupId,
                Mode = FactionCompetitionMode.Pvp,
                RequiredPoint = 0,
                ResetKind = FactionCompetitionResetKind.All
            };
            var state = new FactionCompetitionState(template);
            state.Restore(false, DateTime.MinValue, DateTime.MinValue,
                [new FactionCompetitionPoint(1, 0), new FactionCompetitionPoint(2, 0), new FactionCompetitionPoint(3, 0)]);
            _conquests[zoneGroupId] = state;
        }
    }

    public void OnZoneStateChanged(ushort zoneGroupId, ZoneConflictType previous, ZoneConflictType current, DateTime endsAt)
    {
        if (!_competitions.TryGetValue(zoneGroupId, out var state))
            return;
        var shouldBeActive = MatchesZoneState(state.Template.ZoneStateKind, current);
        if (shouldBeActive)
            StartCompetition(state, DateTime.UtcNow, endsAt);
        else if (MatchesZoneState(state.Template.ZoneStateKind, previous))
            FinishCompetition(state);
    }

    public void OnTowerDefStarted(uint towerDefId, ushort zoneGroupId, DateTime endsAt)
    {
        if (_towerToConquestZone.TryGetValue(towerDefId, out var conquestZone) &&
            _conquests.TryGetValue(conquestZone, out var conquest))
            StartCompetition(conquest, DateTime.UtcNow, endsAt);

        if (_towerToCompetitionZone.TryGetValue(towerDefId, out var competitionZone) &&
            _competitions.TryGetValue(competitionZone, out var competition))
            StartCompetition(competition, DateTime.UtcNow, endsAt);
    }

    public void OnTowerDefEnded(uint towerDefId, ushort zoneGroupId)
    {
        if (_towerToConquestZone.TryGetValue(towerDefId, out var conquestZone) &&
            _conquests.TryGetValue(conquestZone, out var conquest))
            FinishConquest(conquest);

        if (_towerToCompetitionZone.TryGetValue(towerDefId, out var competitionZone) &&
            _competitions.TryGetValue(competitionZone, out var competition))
            FinishCompetition(competition);
    }

    public void OnPcKill(BaseUnit killer, ushort zoneGroupId)
    {
        if (!_competitions.TryGetValue(zoneGroupId, out var state) || !state.Active || state.Template.PcKillPoint <= 0)
            return;
        var factionId = ResolveFactionId(killer, state.Template.Mode);
        AddPoint(state, factionId, (uint)state.Template.PcKillPoint);
    }

    public void OnNpcKill(Character creditOwner, Npc victim, ushort zoneGroupId)
    {
        if (!_competitions.TryGetValue(zoneGroupId, out var state) || !state.Active ||
            state.Template.NpcKillPoint <= 0 || creditOwner == null || victim == null ||
            (!_competitionNpcs.TryGetValue(state.Template.Id, out var npcs) || !npcs.Contains(victim.TemplateId)))
            return;
        AddPoint(state, ResolveFactionId(creditOwner, state.Template.Mode), (uint)state.Template.NpcKillPoint);
    }

    public void OnQuestCompleted(Character character, uint questId)
    {
        if (character == null)
            return;
        var zoneGroupId = CurrentZoneGroup(character);
        if (!_competitions.TryGetValue(zoneGroupId, out var state) || !state.Active ||
            state.Template.QuestCompletePoint <= 0 ||
            (!_competitionQuests.TryGetValue(state.Template.Id, out var quests) || !quests.Contains(questId)))
            return;
        AddPoint(state, ResolveFactionId(character, state.Template.Mode), (uint)state.Template.QuestCompletePoint);
    }

    public void GiveSpecialPoint(BaseUnit actor, uint amount)
    {
        if (actor == null || amount == 0)
            return;
        var zoneGroupId = CurrentZoneGroup(actor);
        if (_competitions.TryGetValue(zoneGroupId, out var competition) && competition.Active)
        {
            AddPoint(competition, ResolveFactionId(actor, competition.Template.Mode), amount);
            return;
        }
        if (_conquests.TryGetValue(zoneGroupId, out var conquest) && conquest.Active)
            AddPoint(conquest, ResolveFactionId(actor, FactionCompetitionMode.Pvp), amount, publishFactionQuest: false);
    }

    public void SyncToCharacter(Character character)
    {
        if (character == null)
            return;
        FactionCompetitionState[] states;
        FactionCompetitionState[] conquests;
        lock (_sync)
        {
            states = _competitions.Values.Where(state => state.Active).ToArray();
            conquests = _conquests.Values.Where(state => state.Active).ToArray();
        }
        var characterZone = CurrentZoneGroup(character);
        foreach (var state in states)
        {
            long duration;
            DateTime startedAt;
            IReadOnlyList<FactionCompetitionPoint> snapshot;
            IReadOnlyDictionary<int, int> ranks;
            lock (_sync)
            {
                startedAt = state.StartedAt;
                duration = Math.Max(0L, (long)(state.EndsAt - state.StartedAt).TotalSeconds);
                snapshot = state.Snapshot();
                ranks = state.GetRanks();
            }
            character.SendPacket(new SCFactionCompetitionPointListPacket(
                characterZone == state.Template.ZoneGroupId,
                state.Template.ZoneGroupId,
                startedAt,
                duration,
                snapshot));

            if (characterZone == state.Template.ZoneGroupId)
            {
                var factionId = ResolveFactionId(character, state.Template.Mode);
                if (ranks.TryGetValue(factionId, out var rank))
                {
                    character.Events.OnQuestObjective(character, new OnQuestObjectiveArgs
                    {
                        Type = QuestObjectiveEventType.FactionCompetition,
                        Actor = character,
                        ZoneGroupId = state.Template.ZoneGroupId,
                        Rank = rank,
                        Result = false,
                        Amount = 1
                    });
                }
            }
        }

        foreach (var state in conquests)
        {
            if (characterZone != state.Template.ZoneGroupId)
                continue;
            IReadOnlyDictionary<int, int> ranks;
            lock (_sync)
                ranks = state.GetRanks();
            var factionId = ResolveFactionId(character, FactionCompetitionMode.Pvp);
            if (!ranks.TryGetValue(factionId, out var rank))
                continue;
            character.Events.OnQuestObjective(character, new OnQuestObjectiveArgs
            {
                Type = QuestObjectiveEventType.ConquestWar,
                Actor = character,
                ZoneGroupId = state.Template.ZoneGroupId,
                Rank = rank,
                Result = false,
                Amount = 1
            });
        }
    }

    private void StartCompetition(FactionCompetitionState state, DateTime startedAt, DateTime endsAt)
    {
        lock (_sync)
        {
            if (!state.Start(startedAt, endsAt > startedAt ? endsAt : startedAt))
                return;
            PersistState(state, IsConquest(state));
        }
        BroadcastPointList(state);
        Logger.Info("Faction competition started zone={0} id={1} ends={2:o}",
            state.Template.ZoneGroupId, state.Template.Id, state.EndsAt);
    }

    private void AddPoint(FactionCompetitionState state, int factionId, uint amount, bool publishFactionQuest = true)
    {
        if (factionId <= 0)
            return;
        uint point;
        IReadOnlyDictionary<int, int> ranks;
        var forceFinish = false;
        lock (_sync)
        {
            point = state.AddPoint(factionId, amount);
            if (!state.Active)
                return;
            ranks = state.GetRanks();
            PersistState(state, IsConquest(state));
            forceFinish = publishFactionQuest && state.Template.ForceChangeState &&
                state.Template.RequiredPoint > 0 && point >= state.Template.RequiredPoint;
        }

        worldManager.BroadcastPacketToServer(new SCFactionCompetitionUpdatePointPacket(
            (short)state.Template.ZoneGroupId, factionId, point));
        if (publishFactionQuest)
            PublishRanks(state, ranks, isResult: false, QuestObjectiveEventType.FactionCompetition);

        if (forceFinish)
        {
            var conflict = zoneManager.GetConflicts().FirstOrDefault(item => item.ZoneGroupId == state.Template.ZoneGroupId);
            if (conflict != null)
                conflict.ForceNextState();
            else
                FinishCompetition(state);
        }
    }

    private void FinishCompetition(FactionCompetitionState state)
    {
        IReadOnlyList<FactionCompetitionPoint> snapshot;
        IReadOnlyDictionary<int, int> ranks;
        int winner;
        lock (_sync)
        {
            if (!state.Active)
                return;
            snapshot = state.Snapshot();
            ranks = state.GetRanks();
            winner = state.ResolveWinner();
            state.FinishAndReset(winner);
            PersistState(state, false);
        }

        worldManager.BroadcastPacketToServer(new SCFactionCompetitionResultPacket(
            state.Template.ZoneGroupId, winner, snapshot));
        PublishRanks(state, ranks, isResult: true, QuestObjectiveEventType.FactionCompetition);

        // ConquestWar zone 20 represents the resulting occupation, not the live purification rank.
        if (winner > 0 && state.Template.ZoneGroupId == 20)
            PublishWinnerConquest(state.Template.ZoneGroupId, winner);

        if (winner > 0 && _winnerTowerDefs.TryGetValue((state.Template.Id, winner), out var winnerTowerDef))
            WorldIntegration.TriggerTowerDef?.Invoke("start", winnerTowerDef, 0);
        if (state.Template.ForceStopTowerDefId != 0)
            WorldIntegration.TriggerTowerDef?.Invoke("end", state.Template.ForceStopTowerDefId, 0);

        Logger.Info("Faction competition ended zone={0} id={1} winner={2}",
            state.Template.ZoneGroupId, state.Template.Id, winner);
    }

    private void FinishConquest(FactionCompetitionState state)
    {
        IReadOnlyDictionary<int, int> ranks;
        lock (_sync)
        {
            if (!state.Active)
                return;
            ranks = state.GetRanks();
            state.FinishAndReset(state.ResolveWinner());
            PersistState(state, true);
        }
        PublishRanks(state, ranks, isResult: true, QuestObjectiveEventType.ConquestWar);
        Logger.Info("Conquest war ended zone={0}", state.Template.ZoneGroupId);
    }

    private void PublishRanks(FactionCompetitionState state, IReadOnlyDictionary<int, int> ranks,
        bool isResult, QuestObjectiveEventType eventType)
    {
        foreach (var character in worldManager.GetAllCharacters())
        {
            if (character is not { IsOnline: true } || CurrentZoneGroup(character) != state.Template.ZoneGroupId)
                continue;
            var factionId = ResolveFactionId(character, state.Template.Mode);
            if (!ranks.TryGetValue(factionId, out var rank))
                continue;
            character.Events.OnQuestObjective(character, new OnQuestObjectiveArgs
            {
                Type = eventType,
                Actor = character,
                ZoneGroupId = state.Template.ZoneGroupId,
                Rank = rank,
                Result = isResult,
                Amount = 1
            });
        }
    }

    private void PublishWinnerConquest(ushort zoneGroupId, int winnerFactionId)
    {
        foreach (var character in worldManager.GetAllCharacters())
        {
            if (character is not { IsOnline: true } || CurrentZoneGroup(character) != zoneGroupId ||
                ResolveFactionId(character, FactionCompetitionMode.Pvp) != winnerFactionId)
                continue;
            character.Events.OnQuestObjective(character, new OnQuestObjectiveArgs
            {
                Type = QuestObjectiveEventType.ConquestWar,
                Actor = character,
                ZoneGroupId = zoneGroupId,
                Rank = 1,
                Result = true,
                Amount = 1
            });
        }
    }

    private void BroadcastPointList(FactionCompetitionState state)
    {
        long duration;
        DateTime startedAt;
        IReadOnlyList<FactionCompetitionPoint> snapshot;
        lock (_sync)
        {
            startedAt = state.StartedAt;
            duration = Math.Max(0L, (long)(state.EndsAt - state.StartedAt).TotalSeconds);
            snapshot = state.Snapshot();
        }
        foreach (var character in worldManager.GetAllCharacters())
        {
            if (character is not { IsOnline: true })
                continue;
            character.SendPacket(new SCFactionCompetitionPointListPacket(
                CurrentZoneGroup(character) == state.Template.ZoneGroupId,
                state.Template.ZoneGroupId, startedAt, duration, snapshot));
        }
    }

    private void ReconcileLoadedZoneStates()
    {
        foreach (var conflict in zoneManager.GetConflicts())
        {
            if (!_competitions.TryGetValue(conflict.ZoneGroupId, out var state) || state.Active ||
                !MatchesZoneState(state.Template.ZoneStateKind, conflict.CurrentZoneState))
                continue;
            state.Start(DateTime.UtcNow, conflict.NextStateTime);
            PersistState(state, false);
        }
    }

    private void LoadPersistentStates()
    {
        using var connection = MySQL.CreateConnection();
        using var command = connection.CreateCommand();
        command.CommandText = @"SELECT kind, source_id, faction_id, points, active, started_at, ends_at
FROM faction_competition_states ORDER BY kind, source_id, faction_id";
        using var reader = command.ExecuteReader();
        var rows = new Dictionary<(byte Kind, uint Source), List<FactionCompetitionPoint>>();
        var metadata = new Dictionary<(byte Kind, uint Source), (bool Active, DateTime Start, DateTime End)>();
        while (reader.Read())
        {
            var key = (reader.GetByte("kind"), reader.GetUInt32("source_id"));
            if (!rows.TryGetValue(key, out var points))
                rows[key] = points = [];
            points.Add(new FactionCompetitionPoint(reader.GetInt32("faction_id"), reader.GetUInt32("points")));
            metadata[key] = (reader.GetBoolean("active"),
                reader.IsDBNull(reader.GetOrdinal("started_at")) ? DateTime.MinValue : reader.GetDateTime("started_at"),
                reader.IsDBNull(reader.GetOrdinal("ends_at")) ? DateTime.MinValue : reader.GetDateTime("ends_at"));
        }

        foreach (var state in _competitions.Values)
        {
            var key = ((byte)0, state.Template.Id);
            if (rows.TryGetValue(key, out var points))
            {
                var meta = metadata[key];
                state.Restore(meta.Active, meta.Start, meta.End, points);
            }
        }
        foreach (var state in _conquests.Values)
        {
            var key = ((byte)1, state.Template.Id);
            if (rows.TryGetValue(key, out var points))
            {
                var meta = metadata[key];
                state.Restore(meta.Active, meta.Start, meta.End, points);
            }
        }
    }

    private static void PersistState(FactionCompetitionState state, bool conquest)
    {
        using var connection = MySQL.CreateConnection();
        using var transaction = connection.BeginTransaction();
        foreach (var point in state.Snapshot())
        {
            using var command = connection.CreateCommand();
            command.Transaction = transaction;
            command.CommandText = @"INSERT INTO faction_competition_states
(kind, source_id, zone_group_id, faction_id, points, active, started_at, ends_at)
VALUES (@kind, @source, @zone, @faction, @points, @active, @started, @ends)
ON DUPLICATE KEY UPDATE points=VALUES(points), active=VALUES(active),
started_at=VALUES(started_at), ends_at=VALUES(ends_at), zone_group_id=VALUES(zone_group_id)";
            command.Parameters.AddWithValue("@kind", conquest ? 1 : 0);
            command.Parameters.AddWithValue("@source", state.Template.Id);
            command.Parameters.AddWithValue("@zone", state.Template.ZoneGroupId);
            command.Parameters.AddWithValue("@faction", point.FactionId);
            command.Parameters.AddWithValue("@points", point.Point);
            command.Parameters.AddWithValue("@active", state.Active);
            command.Parameters.AddWithValue("@started", state.StartedAt == DateTime.MinValue ? DBNull.Value : state.StartedAt);
            command.Parameters.AddWithValue("@ends", state.EndsAt == DateTime.MinValue ? DBNull.Value : state.EndsAt);
            command.ExecuteNonQuery();
        }
        transaction.Commit();
    }

    private bool IsConquest(FactionCompetitionState state) => _conquests.ContainsValue(state);

    private static bool MatchesZoneState(byte kind, ZoneConflictType state) =>
        kind == 1 ? state == ZoneConflictType.Peace : kind == 2 && state == ZoneConflictType.War;

    private ushort CurrentZoneGroup(BaseUnit unit)
    {
        var zone = zoneManager.GetZoneByKey(unit.Transform.ZoneId);
        return zone == null ? (ushort)0 : (ushort)zone.GroupId;
    }

    internal static int ResolveFactionId(BaseUnit actor, FactionCompetitionMode mode)
    {
        if (mode == FactionCompetitionMode.Pve)
            return actor.GetOwnerCharacter() != null ? 4 : 5;
        var faction = actor.GetOwnerCharacter()?.Faction ?? actor.Faction;
        var id = faction != null && faction.MotherId != FactionsEnum.Invalid
            ? faction.MotherId
            : faction?.Id ?? FactionsEnum.Invalid;
        return id switch
        {
            FactionsEnum.NuiaAlliance => 1,
            FactionsEnum.HaranyaAlliance => 2,
            FactionsEnum.Pirate => 3,
            _ => (int)id
        };
    }
}
