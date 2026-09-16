using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Teleport;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Utils;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class Return : SpecialEffectAction
{
    internal enum MainWorldReturnTransport
    {
        TeleportOnly,
        LoadInstance
    }

    internal static MainWorldReturnTransport GetMainWorldReturnTransport(uint currentInstanceId) =>
        currentInstanceId == WorldManager.DefaultInstanceId
            ? MainWorldReturnTransport.TeleportOnly
            : MainWorldReturnTransport.LoadInstance;

    internal static uint? ResolveDestinationInstance(uint currentInstanceId, uint currentWorldId,
        uint? destinationWorldId)
    {
        if (destinationWorldId == null)
            return null;
        if (destinationWorldId == WorldManager.DefaultWorldTemplateId)
            return WorldManager.DefaultInstanceId;
        // An internal portal must keep the player's own copy; never enter another player's copy.
        return destinationWorldId == currentWorldId ? currentInstanceId : null;
    }

    public override void Execute(BaseUnit caster,
        SkillCaster casterObj,
        BaseUnit target,
        SkillCastTarget targetObj,
        CastAction castObj,
        Skill skill,
        SkillObject skillObject,
        DateTime time,
        int value1,
        int value2,
        int value3,
        int value4)
    {
        // TODO ...
        if (caster is Character) { Logger.Info("Special effects: Return value1 {0}, value2 {1}, value3 {2}, value4 {3}", value1, value2, value3, value4); }

        if (caster is not Character character) { return; }
        uint returnPointId;
        Portal trp;

        // first check for an entry in the return book
        if (value1 == 0)
        {
            // Memory Tome for Recall skill
            returnPointId = PortalManager.Instance.GetDistrictReturnPoint(character.ReturnDistrictId, character.Faction.Id);
            trp = PortalManager.Instance.GetRecallById(returnPointId);
            if (returnPointId == 0) { return; }
        }
        else
        {
            // Explicit Return destinations can be worldgates or normal return points. For
            // example, AA10 skill 42067 carries return point 18 (Lacton) from recalls.json.
            returnPointId = (uint)value1;
            trp = PortalManager.Instance.GetReturnDestinationById(returnPointId);
        }

        if (trp == null)
        {
            Logger.Warn("Return refused: character={0}, point={1}; destination is not registered",
                character.Id, returnPointId);
            character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
            return;
        }

        if (trp != null)
        {
            // Check before changing position: SetPosition initiates the Zone handoff and
            // disconnects the character when no host owns the destination.
            if (WorldIntegration.ZoneAuthority &&
                WorldIntegration.IsZoneLoaded?.Invoke(trp.ZoneId) != true)
            {
                Logger.Warn("Return refused before teleport: character={0}, point={1}, zone={2}; destination host unavailable",
                    character.Id, returnPointId, trp.ZoneId);
                character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
                return;
            }

            var destinationWorld = WorldManager.Instance.GetWorldTemplateByZoneKey(trp.ZoneId);
            var destinationInstanceId = ResolveDestinationInstance(character.Transform.InstanceId,
                character.Transform.WorldId, destinationWorld?.Id);
            if (destinationInstanceId == null)
            {
                Logger.Warn("Return refused: character={0}, point={1}; destination needs a separate instance entry",
                    character.Id, returnPointId);
                character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
                return;
            }
            // A same-instance Return streams the destination without reloading the world.
            if (character.Transform.InstanceId != destinationInstanceId.Value)
            {
                character.DisabledSetPosition = true;
                character.SendPacket(
                    new SCLoadInstancePacket(
                        destinationInstanceId.Value,
                        trp.ZoneId,
                        trp.X,
                        trp.Y,
                        trp.Z,
                        0,
                        0,
                        trp.Yaw.DegToRad()
                    )
                );

                character.Transform = new Transform(
                    character,
                    null,
                    trp.ZoneId,
                    destinationInstanceId.Value,
                    trp.X,
                    trp.Y,
                    trp.Z,
                    trp.Yaw.DegToRad());
            }
            else
            {
                var yaw = trp.Yaw.DegToRad();
                character.DisabledSetPosition = false;
                character.SetPosition(trp.X, trp.Y, trp.Z, 0f, 0f, yaw);
                character.Transform.FinalizeTransform();
            }
            //character.MainWorldPosition = null; // we will not delete the return point to the main world
        }
        caster.DisabledSetPosition = true;
        character.SendPacket(
            new SCTeleportUnitPacket(
            TeleportReason.MoveToLocation,
            0,
            trp.X,
            trp.Y,
            trp.Z,
            trp.Yaw.DegToRad()));
    }
}
