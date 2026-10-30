using AAEmu.Game.Models;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

public readonly record struct MechanicsSandboxIdentity(
    uint CharacterId, uint AccountId, string Name, uint WorldId, uint InstanceId, uint ZoneKey);

public static class MechanicsSandboxPolicy
{
    public static string Validate(MechanicsSandboxConfig config, MechanicsSandboxIdentity actor)
    {
        if (!config.Enabled)
            return "El sandbox está desactivado en este entorno.";
        if (config.CharacterId == 0 || config.AccountId == 0 || string.IsNullOrWhiteSpace(config.CharacterName))
            return "Falta vincular el personaje y la cuenta exclusivos del sandbox.";
        if (actor.CharacterId != config.CharacterId || actor.AccountId != config.AccountId ||
            !string.Equals(actor.Name, config.CharacterName, StringComparison.Ordinal))
            return "Este personaje no pertenece al sandbox configurado.";
        if (actor.WorldId != config.WorldId || actor.InstanceId != config.InstanceId || actor.ZoneKey != config.ZoneKey)
            return "El personaje debe entrar primero en la zona configurada del sandbox.";
        if (config.ZoneKey == 0 || config.DummyTemplateId == 0 || config.Origin == null ||
            !Finite(config.Origin.X, config.Origin.Y, config.Origin.Z, config.Origin.Rotation))
            return "El origen del escenario no es válido.";
        if (config.Dummies == null || config.Dummies.Count is < 1 or > 16 || config.Dummies.Any(d =>
                d == null || !Finite(d.Forward, d.Right, d.Up) ||
                Math.Abs(d.Forward) > 60 || Math.Abs(d.Right) > 60 || Math.Abs(d.Up) > 10))
            return "El escenario requiere entre 1 y 16 dummies con posiciones locales válidas.";
        if (string.IsNullOrWhiteSpace(config.SceneName))
            return "El escenario requiere un nombre válido.";
        if (config.Services.Count > 8 || config.Services.Any(service =>
                service == null || service.TemplateId == 0 || !ValidRole(service.Role) ||
                !Finite(service.Forward, service.Right, service.Up, service.Rotation) ||
                Math.Abs(service.Forward) > 60 || Math.Abs(service.Right) > 60 || Math.Abs(service.Up) > 10) ||
            config.Services.Select(service => service.Role).Distinct(StringComparer.Ordinal).Count() != config.Services.Count)
            return "Los servicios requieren hasta 8 NPCs con roles únicos y posiciones locales válidas.";
        return null;
    }

    /// <summary>Plans a detached layout update; rejected requests cannot mutate the active profile.</summary>
    public static bool TryPlanAdjustment(MechanicsSandboxConfig current, MechanicsSandboxConfig proposed,
        out MechanicsSandboxConfig plan, out string error)
    {
        plan = null;
        if (current == null || proposed == null || current.Enabled != proposed.Enabled ||
            current.CombatProfile != proposed.CombatProfile ||
            current.CharacterId != proposed.CharacterId || current.AccountId != proposed.AccountId ||
            !string.Equals(current.CharacterName, proposed.CharacterName, StringComparison.Ordinal) ||
            current.WorldId != proposed.WorldId || current.InstanceId != proposed.InstanceId ||
            current.ZoneKey != proposed.ZoneKey || current.DummyTemplateId != proposed.DummyTemplateId ||
            !string.Equals(current.SceneName, proposed.SceneName, StringComparison.Ordinal) ||
            !SameServices(current.Services, proposed.Services))
        {
            error = "La configuración en vivo sólo puede cambiar el origen y las posiciones de los dummies.";
            return false;
        }
        error = Validate(proposed, new MechanicsSandboxIdentity(current.CharacterId, current.AccountId,
            current.CharacterName, current.WorldId, current.InstanceId, current.ZoneKey));
        if (error != null)
            return false;
        plan = new MechanicsSandboxConfig
        {
            Enabled = current.Enabled, CombatProfile = current.CombatProfile, CharacterId = current.CharacterId, AccountId = current.AccountId,
            CharacterName = current.CharacterName, WorldId = current.WorldId, InstanceId = current.InstanceId,
            ZoneKey = current.ZoneKey, DummyTemplateId = current.DummyTemplateId,
            SceneName = current.SceneName,
            Origin = new MechanicsSandboxOrigin
            { X = proposed.Origin.X, Y = proposed.Origin.Y, Z = proposed.Origin.Z, Rotation = proposed.Origin.Rotation },
            Dummies = proposed.Dummies.Select(dummy => new MechanicsSandboxDummy
            { Forward = dummy.Forward, Right = dummy.Right, Up = dummy.Up }).ToList(),
            Services = current.Services.Select(service => new MechanicsSandboxServiceNpc
            {
                TemplateId = service.TemplateId, Role = service.Role, Forward = service.Forward,
                Right = service.Right, Up = service.Up, Rotation = service.Rotation
            }).ToList()
        };
        return true;
    }

    private static bool Finite(params float[] values) => values.All(float.IsFinite);

    private static bool ValidRole(string role) => role is "specializations" or "warehouse" or "weapons" or "armor";

    private static bool SameServices(List<MechanicsSandboxServiceNpc> current, List<MechanicsSandboxServiceNpc> proposed)
    {
        if (current.Count != proposed.Count)
            return false;
        for (var i = 0; i < current.Count; i++)
        {
            var left = current[i];
            var right = proposed[i];
            if (left == null || right == null || left.TemplateId != right.TemplateId ||
                !string.Equals(left.Role, right.Role, StringComparison.Ordinal) ||
                left.Forward != right.Forward || left.Right != right.Right || left.Up != right.Up ||
                left.Rotation != right.Rotation)
                return false;
        }
        return true;
    }
}
