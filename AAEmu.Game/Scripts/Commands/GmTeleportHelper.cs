using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Teleport;

namespace AAEmu.Game.Scripts.Commands;

/// <summary>
/// Keeps GM same-world teleports authoritative in both Game and the native Zone process.
/// </summary>
internal static class GmTeleportHelper
{
    public static bool TryTeleport(
        Character character,
        float x,
        float y,
        float z,
        float yaw,
        out string error)
    {
        error = string.Empty;
        var worldTemplate = character.ParentWorld?.Template;
        if (worldTemplate == null)
        {
            error = "The target character has no active world.";
            return false;
        }

        var destinationZoneId = WorldManager.Instance.GetZoneId(worldTemplate, x, y);
        if (destinationZoneId == 0)
        {
            error = $"Position X:{x:0.0} Y:{y:0.0} is outside the active world.";
            return false;
        }

        if (WorldIntegration.ZoneAuthority &&
            WorldIntegration.IsZoneLoaded != null &&
            !WorldIntegration.IsZoneLoaded(destinationZoneId))
        {
            error = $"Zone {destinationZoneId} is not loaded.";
            return false;
        }

        // Update Game first. Character.SetPosition observes the zone-key change and performs the
        // WZUnitRemoved -> WZUnitState handoff before the client starts reporting movement there.
        character.ForceDismount();
        character.SetPosition(x, y, z, 0f, 0f, yaw);
        character.Transform.FinalizeTransform();
        if (character.Transform.ZoneId != destinationZoneId)
        {
            error = $"Could not resolve destination zone {destinationZoneId}.";
            return false;
        }

        character.DisabledSetPosition = true;
        character.SendPacket(new SCTeleportUnitPacket(TeleportReason.Gm, 0, x, y, z, yaw));
        return true;
    }
}
