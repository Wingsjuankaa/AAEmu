using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Teleport;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSTeleportEndedPacket() : GamePacket(CSOffsets.CSTeleportEndedPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var x = Helpers.ConvertLongX(stream.ReadInt64());
        var y = Helpers.ConvertLongY(stream.ReadInt64());
        var z = stream.ReadSingle();
        var ori = stream.ReadBytes(16); // TODO example: 00000000 00000000 00000000 0000803F

        var character = Connection.ActiveChar;
        character.DisabledSetPosition = false;

        var worldTemplate = character.ParentWorld?.Template;
        var destinationZoneId = worldTemplate == null
            ? 0
            : WorldManager.Instance.GetZoneId(worldTemplate, x, y);
        if (destinationZoneId == 0 ||
            WorldIntegration.ZoneAuthority &&
            WorldIntegration.IsZoneLoaded != null &&
            !WorldIntegration.IsZoneLoaded(destinationZoneId))
        {
            Logger.Error(
                "TeleportEnded rejected for {0}: destination zone {1} is unavailable at ({2:F1},{3:F1},{4:F1})",
                character.Name, destinationZoneId, x, y, z);
            character.SendErrorMessage(ErrorMessageType.TeleporterInvalidLocation);
            var rollback = character.Transform.World;
            character.DisabledSetPosition = true;
            character.SendPacket(new SCTeleportUnitPacket(
                TeleportReason.Gm,
                0,
                rollback.Position.X,
                rollback.Position.Y,
                rollback.Position.Z,
                rollback.Rotation.Z));
            return;
        }

        // GM teleports historically moved only the client. Applying the acknowledged position here is
        // the final safety net; commands now move Game before sending SCTeleportUnit, so this is normally
        // an idempotent same-zone update and never repeats the handoff.
        var rotation = character.Transform.World.Rotation;
        character.SetPosition(x, y, z, rotation.X, rotation.Y, rotation.Z);
        character.Transform.FinalizeTransform();
        Logger.Info("TeleportEnded {0}: zone={1} X={2:F1} Y={3:F1} Z={4:F1}",
            character.Name, character.Transform.ZoneId, x, y, z);

        WorldManager.ResendVisibleObjectsToCharacter(character);
    }
}
