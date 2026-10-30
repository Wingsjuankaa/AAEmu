using System.Diagnostics;
using System.Text.Json;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;
using AAEmu.Game.Scripts.Commands;
using NLog;

namespace AAEmu.Game.Core.Managers;

/// <summary>
/// Scoped development controls over the real Character/Npc/Skill pipeline. No simulation substitutes,
/// no persistence reset, and no native Zone lifecycle operations are performed by this manager.
/// </summary>
public sealed class MechanicsSandboxManager
{
    public static MechanicsSandboxManager Instance { get; } = new();
    private static readonly Logger s_logger = LogManager.GetCurrentClassLogger();
    private readonly object _gate = new();
    private Session _session;
    private Task _operation;
    private static readonly JsonSerializerOptions s_json = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    private sealed class Session(Character character, MechanicsSandboxConfig config)
    {
        public Character Character { get; } = character;
        public MechanicsSandboxConfig Config { get; set; } = config;
        public MechanicsSandboxExecution.Scope Execution { get; } = new();
        public List<Npc> Dummies { get; } = [];
        private List<(Npc Actor, MechanicsSandboxServiceNpc Definition)> _services;
        public List<(Npc Actor, MechanicsSandboxServiceNpc Definition)> Services => _services ??= [];
        public List<MechanicsSandboxBuffSnapshot> BaselineBuffs { get; } = [];
        public MechanicsSandboxPassiveBaseline PassiveBaseline { get; set; }
        public string State { get; set; } = "initializing";
        public string Message { get; set; } = "Preparando el escenario.";
        public int Attempt { get; set; }
    }

    public sealed record Status(bool Success, string State, string Message, uint CharacterId, string Character,
        uint ZoneKey, int Attempt, uint[] Dummies, int Hp, int Mp)
    {
        public MechanicsSandboxOrigin Origin { get; init; }
        public MechanicsSandboxDummy[] Layout { get; init; } = [];
        public string SceneName { get; init; }
        public bool CombatProfile { get; init; }
        public ServiceStatus[] Services { get; init; } = [];
    }

    public sealed record ServiceStatus(uint ObjectId, uint TemplateId, string Role);

    public string ConfigureProfile(Character character, MechanicsSandboxConfig proposed)
    {
        lock (_gate)
        {
            var current = AppConfiguration.Instance.MechanicsSandbox;
            if (proposed == null || current.Enabled != proposed.Enabled ||
                current.CharacterId != proposed.CharacterId || current.AccountId != proposed.AccountId ||
                current.CharacterName != proposed.CharacterName || current.WorldId != proposed.WorldId ||
                current.InstanceId != proposed.InstanceId || current.ZoneKey != proposed.ZoneKey ||
                current.DummyTemplateId != proposed.DummyTemplateId)
                return Serialize(ProfileStatus(character, current, false, "rejected",
                    "El perfil no puede cambiar la identidad, autoridad ni plantilla de objetivos del sandbox."));
            var error = Validate(character, proposed);
            if (error == null)
            {
                try { MechanicsSandboxPassiveBaseline.Capture(character, GetBuffs(character)).Validate(character); }
                catch (InvalidOperationException exception) { error = exception.Message; }
            }
            if (error != null)
                return Serialize(ProfileStatus(character, proposed, false, "rejected", error));
            // Only the sandbox profile changes; scene retirement is a separate explicit operation.
            AppConfiguration.Instance.MechanicsSandbox = Clone(proposed);
            return Serialize(ProfileStatus(character, proposed, true, "validated",
                "Perfil de laboratorio validado y publicado; el escenario actual conserva sus actores."));
        }
    }

    public string Reconfigure(Character character, MechanicsSandboxConfig proposed)
    {
        lock (_gate)
        {
            var error = Validate(character, AppConfiguration.Instance.MechanicsSandbox);
            if (error == null && (_session == null || !ReferenceEquals(_session.Character, character) ||
                                  _session.State != "ready" || _operation is { IsCompleted: false }))
                error = "El escenario debe estar listo antes de aplicar una configuración en vivo.";
            if (error == null && (character.IsRiding || character.HasPendingSlaves || character.IsInDuel ||
                                  GetBuffs(character).Any(buff => buff.ZoneAuthored)))
                error = "El estado actual no admite restauración del escenario en vivo.";
            MechanicsSandboxConfig plan = null;
            if (error == null && !MechanicsSandboxPolicy.TryPlanAdjustment(_session.Config, proposed, out plan, out error))
                error ??= "La configuración en vivo no es válida.";
            if (error == null)
                error = Validate(character, plan);
            if (error == null)
            {
                try { _session.PassiveBaseline?.Validate(character); }
                catch (InvalidOperationException exception) { error = exception.Message; }
            }
            if (error != null)
                return Serialize(new Status(false, "rejected", error, character.Id, character.Name,
                    character.Transform.ZoneId, _session?.Attempt ?? 0, _session?.Dummies.Select(npc => npc.ObjId).ToArray() ?? [],
                    character.Hp, character.Mp));

            // Native ownership and every proposed position were checked before retiring an attempt.
            StartOperation(_session, clear: false, adjustment: plan);
            return Serialize(Snapshot(character));
        }
    }

    public string Execute(Character character, string action)
    {
        lock (_gate)
        {
            var config = AppConfiguration.Instance.MechanicsSandbox;
            var error = Validate(character, config);
            if (error != null)
            {
                if (action == "validate")
                    return Serialize(ProfileStatus(character, config, false, "rejected", error));
                return Serialize(new Status(false, "rejected", error, character.Id, character.Name,
                    character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
            }
            if (action == "status")
                return Serialize(Snapshot(character));
            if (action == "validate")
            {
                try
                {
                    MechanicsSandboxPassiveBaseline.Capture(character, GetBuffs(character)).Validate(character);
                    return Serialize(ProfileStatus(character, config, true, "validated",
                        "Perfil, servicios y baseline admitidos sin modificar el escenario."));
                }
                catch (InvalidOperationException exception)
                {
                    return Serialize(ProfileStatus(character, config, false, "rejected", exception.Message));
                }
            }
            if (action is not ("begin" or "reset" or "clear"))
                return Serialize(new Status(false, "rejected", "Acción válida: begin, status, reset o clear.",
                    character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
            if (GetBuffs(character).Any(buff => buff.ZoneAuthored))
                return Serialize(new Status(false, "rejected", "La restauración V1 no reconstruye buffs administrados por Zone; termina ese estado antes de restablecer el escenario.",
                    character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
            if (_operation is { IsCompleted: false })
                return Serialize(Snapshot(character));
            try
            {
                if (_session != null && ReferenceEquals(_session.Character, character))
                    _session.PassiveBaseline?.Validate(character);
            }
            catch (InvalidOperationException exception)
            {
                return Serialize(new Status(false, "rejected", exception.Message, character.Id, character.Name,
                    config.ZoneKey, _session?.Attempt ?? 0, [], character.Hp, character.Mp));
            }

            if (_session != null && !ReferenceEquals(_session.Character, character))
            {
                if (MechanicsSandboxSessions.IsCurrent(_session.Character, GameConnectionTable.Instance.GetConnections()))
                    return Serialize(new Status(false, "rejected", "Ya hay otra sesión del sandbox activa.",
                        character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
                RemoveDummies(_session);
                _session.Execution.Dispose();
                _session = null;
            }

            if (action == "clear")
            {
                if (_session == null)
                    return Serialize(Snapshot(character));
                StartOperation(_session, clear: true);
                return Serialize(Snapshot(character));
            }

            if (_session == null)
            {
                if (action == "reset")
                    return Serialize(new Status(false, "rejected", "Inicia primero el escenario con begin.",
                        character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
                if (character.SkillTask != null || character.ActivePlotState != null || character.IsInBattle)
                    return Serialize(new Status(false, "rejected", "Espera a que termine el combate antes de iniciar el escenario.",
                        character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
                var baselineBuffs = GetBuffs(character);
                if (baselineBuffs.Any(buff => buff.ZoneAuthored))
                    return Serialize(new Status(false, "rejected", "El baseline contiene buffs administrados por Zone; no se puede restaurar con autoridad World.",
                        character.Id, character.Name, character.Transform.ZoneId, 0, [], character.Hp, character.Mp));
                MechanicsSandboxPassiveBaseline passiveBaseline;
                try { passiveBaseline = MechanicsSandboxPassiveBaseline.Capture(character, baselineBuffs); }
                catch (InvalidOperationException exception)
                {
                    return Serialize(new Status(false, "rejected", exception.Message, character.Id, character.Name,
                        config.ZoneKey, 0, [], character.Hp, character.Mp));
                }
                _session = new Session(character, Clone(config)) { PassiveBaseline = passiveBaseline };
                _session.Execution.AddActor(character);
                _session.BaselineBuffs.AddRange(baselineBuffs.Select(MechanicsSandboxBuffSnapshot.Capture));
            }
            // A repeated begin is idempotent; reset is the explicit next attempt.
            if (action == "begin" && _session.State == "ready")
                return Serialize(Snapshot(character));
            StartOperation(_session, clear: false);
            return Serialize(Snapshot(character));
        }
    }

    private void StartOperation(Session session, bool clear, MechanicsSandboxConfig adjustment = null)
    {
        var previousConfig = session.Config;
        session.State = clear ? "clearing" : "resetting";
        session.Message = clear ? "Cerrando el escenario." : "Restableciendo el escenario.";
        // Retire the old epoch synchronously before acknowledging reset to the caller.
        var skills = session.Execution.BeginReset();
        _operation = Task.Run(async () =>
        {
            try
            {
                foreach (var (skill, caster) in skills)
                {
                    skill.Cancelled = true;
                    skill.ActivePlotState?.RequestCancellation();
                    if (skill.TlId != 0)
                        skill.Stop(caster);
                }
                StopActor(session.Character);
                // A packet-side craft holds its session lock before entering Skill.Use. Cancel it
                // before taking the execution gate for baseline mutation, avoiding lock inversion.
                session.Character.Craft?.Cancel();
                foreach (var npc in session.Dummies.ToArray())
                    StopActor(npc);
                foreach (var service in session.Services.ToArray())
                    StopActor(service.Actor);

                // Plot cancellation is handled by its existing scheduler/end path. Wait for that path,
                // while the epoch fence rejects every old event/projectile and all new sandbox casts.
                var deadline = Stopwatch.StartNew();
                while (skills.Any(pair => pair.Skill.ActivePlotState != null))
                {
                    if (deadline.Elapsed > TimeSpan.FromSeconds(15))
                        throw new InvalidOperationException("Una habilidad no terminó su cancelación; el escenario sigue bloqueado.");
                    await Task.Delay(25).ConfigureAwait(false);
                }

                lock (_gate)
                {
                    session.Execution.Mutate(() =>
                    {
                    if (adjustment != null)
                    {
                        var adjustmentError = Validate(session.Character, adjustment);
                        if (adjustmentError != null)
                            throw new InvalidOperationException(adjustmentError);
                        session.Config = adjustment;
                    }
                    RemoveDummies(session);
                    if (clear)
                    {
                        // New baseline callbacks must become ordinary callbacks after detaching. Old
                        // scenario callbacks retain their retired scope/epoch and can never re-enter.
                        session.Execution.RemoveActor(session.Character);
                        RestoreBuffs(session, session.Execution);
                        session.Execution.Dispose();
                        _session = null;
                        return;
                    }
                    var error = Validate(session.Character, session.Config);
                    if (error != null)
                        throw new InvalidOperationException(error);
                    ResetCharacter(session);
                    SpawnDummies(session);
                    SpawnServices(session);
                    session.Attempt++;
                    session.State = "ready";
                    session.Message = "Escenario listo: mecánicas y cooldowns normales activos.";
                    session.Execution.CompleteReset();
                    s_logger.Info("MechanicsSandbox ready character={0} attempt={1} dummies={2}",
                        session.Character.Id, session.Attempt, string.Join(',', session.Dummies.Select(n => n.ObjId)));
                    s_logger.Info("MechanicsSandbox services character={0} actors={1}", session.Character.Id,
                        string.Join(',', session.Services.Select(service => $"{service.Definition.Role}:{service.Actor.ObjId}:{service.Actor.TemplateId}")));
                    });
                }
            }
            catch (Exception exception)
            {
                lock (_gate)
                {
                    session.Config = previousConfig;
                    try { RemoveDummies(session); }
                    catch (Exception cleanupError)
                    {
                        s_logger.Error(cleanupError, "MechanicsSandbox cleanup also failed character={0}", session.Character.Id);
                    }
                    if (clear && MechanicsSandboxExecution.Capture(session.Character).Owner == null)
                        session.Execution.AddActor(session.Character);
                    session.State = "faulted";
                    session.Message = exception.Message;
                    // Keep the fence closed until an explicit retry/clear; never report partial reset ready.
                    s_logger.Error(exception, "MechanicsSandbox reset failed character={0}", session.Character.Id);
                }
            }
        });
    }

    private static string Validate(Character character, MechanicsSandboxConfig config)
    {
        var error = MechanicsSandboxPolicy.Validate(config, new MechanicsSandboxIdentity(character.Id,
            character.AccountId, character.Name, character.Transform.WorldId, character.Transform.InstanceId,
            character.Transform.ZoneId));
        if (error != null)
            return error;
        if (!character.IsOnline || !character.WorldEntryCompleted || character.ParentWorld?.Template == null)
            return "El personaje aún no terminó la entrada al mundo.";
        if (!WorldIntegration.ZoneAuthority || WorldIntegration.IsZoneLoaded?.Invoke(config.ZoneKey) != true)
            return "La Zone nativa configurada no está cargada.";
        if (!NpcManager.Instance.Exist(config.DummyTemplateId))
            return "El dummy no existe en los datos AA10 activos.";
        foreach (var service in config.Services)
        {
            var template = NpcManager.Instance.GetTemplate(service.TemplateId);
            if (!MechanicsSandboxServicePolicy.SupportsRole(template, service.Role,
                    QuestManager.Instance.IsQuestTalkNpc(service.TemplateId)))
                return $"La plantilla {service.TemplateId} no ofrece el servicio nativo {service.Role} en este runtime.";
        }
        var points = config.Dummies.Select(dummy => Position(config.Origin, dummy))
            .Concat(config.Services.Select(service => Position(config.Origin, new MechanicsSandboxDummy
            { Forward = service.Forward, Right = service.Right, Up = service.Up })))
            .Append((config.Origin.X, config.Origin.Y, config.Origin.Z));
        if (points.Any(point => WorldManager.Instance.GetZoneId(character.ParentWorld.Template, point.Item1, point.Item2) != config.ZoneKey))
            return "El origen o un dummy queda fuera de la Zone configurada.";
        return null;
    }

    private static void StopActor(Unit actor)
    {
        actor.ActivePlotState?.RequestCancellation();
        actor.SkillTask?.Cancel();
        actor.SkillTask?.Skill?.Stop(actor);
        actor.AutoAttackTask?.Cancel();
        actor.AutoAttackTask?.Skill?.StopSkill(actor);
        actor.AutoAttackTask = null;
        actor.IsAutoAttack = false;
        actor.ActiveSkillController?.End();
        actor.ActiveSkillController = null;
        actor.CurrentTarget = null;
        actor.CurrentInteractionObject = null;
        actor.ClearAllAggro();
        actor.IsInBattle = false;
        actor.BroadcastPacket(new SCTargetChangedPacket(actor.ObjId, 0), true);
        if (WorldIntegration.ZoneAuthority)
        {
            WorldIntegration.RelayTargetChangedToZone?.Invoke(actor.ObjId, 0, true);
            WorldIntegration.RelayCombatClearedToZone?.Invoke(actor.ObjId);
        }
    }

    private static void ResetCharacter(Session session)
    {
        var actor = session.Character;
        RestoreBuffs(session, session.Execution);
        var origin = session.Config.Origin;
        if (actor.Hp == 0)
            Revive.ReviveCharacter(actor);
        if (!GmTeleportHelper.TryTeleport(actor, origin.X, origin.Y, origin.Z, origin.Rotation, out var error))
            throw new InvalidOperationException(error);
        WorldManager.RepositionVisibleObject(actor);
        var oldHp = actor.Hp;
        actor.Hp = actor.MaxHp;
        actor.Mp = actor.MaxMp;
        actor.IsInAggroListOf.Clear();
        actor.ClearAllAggro();
        actor.IsInBattle = false;
        actor.GlobalCooldown = DateTime.MinValue;
        actor.SkillLastUsed = DateTime.MinValue;
        actor.Cooldowns = new UnitCooldowns();
        actor.ResetAllSkillCooldowns(false);
        actor.Buffs.SetToleranceStep(0, 0);
        foreach (var (resource, amount) in actor.CombatResources.ToArray())
            if (amount != 0)
                actor.AddCombatResource(resource, -amount);
        actor.BroadcastPacket(new SCUnitPointsPacket(actor.ObjId, actor.Hp, actor.Mp), true);
        WorldIntegration.RelayUnitPointsToZone?.Invoke(actor.ObjId, actor.Hp, actor.Mp);
        actor.PostUpdateCurrentHp(actor, oldHp, actor.Hp, KillReason.Unknown);
    }

    private static void RestoreBuffs(Session session, MechanicsSandboxExecution.Scope restoration)
    {
        var actor = session.Character;
        if (session.PassiveBaseline != null)
        {
            session.PassiveBaseline.Restore(actor, restoration);
            return;
        }
        // Only an already-running pre-upgrade scene lacks this object; retire it before applying the hub.
        // Recreate the captured baseline, including passive timers, in the new reset epoch.
        // Their real templates/stack/duration still run through the normal Buffs consumer.
        foreach (var buff in GetBuffs(actor))
            buff.Exit();
        foreach (var baseline in session.BaselineBuffs)
        {
            var template = SkillManager.Instance.GetBuffTemplate(baseline.TemplateId);
            if (template == null)
                throw new InvalidOperationException($"Falta el buff inicial {baseline.TemplateId}.");
            var buff = baseline.Create(actor, template);
            if (actor.Buffs is not Buffs buffs)
                throw new InvalidOperationException("El sandbox requiere el consumidor de buffs real.");
            buffs.RestoreMechanicsSnapshot(buff, baseline.EffectiveDuration, restoration);
        }
    }

    private static void SpawnDummies(Session session)
    {
        foreach (var offset in session.Config.Dummies)
        {
            var npc = NpcManager.Instance.CreateMechanicsSandbox(session.Character.ParentWorld, session.Config.DummyTemplateId,
                created =>
                {
                    session.Dummies.Add(created);
                    session.Execution.AddActor(created);
                })
                      ?? throw new InvalidOperationException("No se pudo crear un dummy.");
            // The factory registers the owned actor before its initial buffs/tasks are constructed.
            var position = Position(session.Config.Origin, offset);
            npc.Transform = session.Character.Transform.CloneDetached(npc);
            npc.Transform.Local.SetPosition(position.X, position.Y, position.Z, 0f, 0f,
                session.Config.Origin.Rotation + MathF.PI);
            npc.IsZoneMirror = true;
            npc.Spawn();
            if (!WorldIntegration.PublishNpcSpawn(npc))
                throw new InvalidOperationException("La Zone no aceptó el dummy; se retiró el escenario parcial.");
        }
    }

    private static void SpawnServices(Session session)
    {
        foreach (var definition in session.Config.Services)
        {
            var npc = NpcManager.Instance.CreateMechanicsSandbox(session.Character.ParentWorld, definition.TemplateId,
                created =>
                {
                    session.Services.Add((created, definition));
                    session.Execution.AddActor(created);
                }) ?? throw new InvalidOperationException("No se pudo crear un NPC del laboratorio.");
            var point = Position(session.Config.Origin, new MechanicsSandboxDummy
            { Forward = definition.Forward, Right = definition.Right, Up = definition.Up });
            npc.Transform = session.Character.Transform.CloneDetached(npc);
            npc.Transform.Local.SetPosition(point.X, point.Y, point.Z, 0f, 0f,
                session.Config.Origin.Rotation + definition.Rotation);
            npc.IsZoneMirror = true;
            npc.Spawn();
            if (!WorldIntegration.PublishNpcSpawn(npc))
                throw new InvalidOperationException("La Zone no aceptó un NPC del laboratorio.");
        }
    }

    private static void RemoveDummies(Session session)
    {
        List<Exception> failures = [];
        foreach (var npc in session.Dummies.Concat(session.Services.Select(service => service.Actor)).ToArray())
        {
            try
            {
                // Own references, not a template/radius search: never remove another scenario's unit.
                StopActor(npc);
                npc.Buffs.RemoveAllEffects();
                WorldIntegration.RemoveNpcNow(npc);
                session.Execution.RemoveActor(npc);
                session.Dummies.Remove(npc);
                session.Services.RemoveAll(service => ReferenceEquals(service.Actor, npc));
            }
            catch (Exception exception)
            {
                failures.Add(exception);
            }
        }
        if (failures.Count > 0)
            throw new AggregateException("No se pudieron retirar todos los dummies del escenario.", failures);
    }

    private Status Snapshot(Character character) => _session == null
        ? new Status(true, "idle", "No hay un escenario activo.", character.Id, character.Name,
            character.Transform.ZoneId, 0, [], character.Hp, character.Mp)
        : new Status(_session.State != "faulted", _session.State, _session.Message, _session.Character.Id,
            _session.Character.Name, _session.Config.ZoneKey, _session.Attempt,
            _session.Dummies.Select(n => n.ObjId).ToArray(), _session.Character.Hp, _session.Character.Mp)
        {
            SceneName = _session.Config.SceneName,
            CombatProfile = _session.Config.CombatProfile,
            Services = _session.Services.Select(service => new ServiceStatus(service.Actor.ObjId,
                service.Actor.TemplateId, service.Definition.Role)).ToArray(),
            Origin = new MechanicsSandboxOrigin
            { X = _session.Config.Origin.X, Y = _session.Config.Origin.Y, Z = _session.Config.Origin.Z, Rotation = _session.Config.Origin.Rotation },
            Layout = _session.Config.Dummies.Select(dummy => new MechanicsSandboxDummy
            { Forward = dummy.Forward, Right = dummy.Right, Up = dummy.Up }).ToArray()
        };

    private static Status ProfileStatus(Character character, MechanicsSandboxConfig config, bool success, string state, string message) =>
        new(success, state, message, character.Id, character.Name, config.ZoneKey, 0, [], character.Hp, character.Mp)
        {
            SceneName = config.SceneName,
            CombatProfile = config.CombatProfile,
            Services = config.Services.Where(service => service != null).Select(service =>
                new ServiceStatus(0, service.TemplateId, service.Role)).ToArray()
        };

    private static List<Buff> GetBuffs(Unit actor)
    {
        List<Buff> good = [], bad = [], hidden = [];
        actor.Buffs.GetAllBuffs(good, bad, hidden, true);
        return good.Concat(bad).Concat(hidden).ToList();
    }

    private static (float X, float Y, float Z) Position(MechanicsSandboxOrigin origin, MechanicsSandboxDummy offset)
    {
        // Use the same Transform helpers as the GM spawn commands; yaw convention belongs to the game.
        var position = new Models.Game.World.Transform.PositionAndRotation(origin.X, origin.Y, origin.Z, 0, 0, origin.Rotation);
        position.AddDistanceToFront(offset.Forward);
        position.AddDistanceToRight(offset.Right);
        return (position.Position.X, position.Position.Y, position.Position.Z + offset.Up);
    }

    private static MechanicsSandboxConfig Clone(MechanicsSandboxConfig config) =>
        JsonSerializer.Deserialize<MechanicsSandboxConfig>(JsonSerializer.Serialize(config));

    private static string Serialize(Status status) => JsonSerializer.Serialize(status, s_json);
}
