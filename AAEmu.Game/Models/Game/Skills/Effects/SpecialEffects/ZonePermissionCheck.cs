using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>
/// Local public-Garden policy for the five authored r575 door destinations.
/// Value1=149 is preserved as an opaque permission selector, not interpreted as a zone id.
/// Other selectors and non-public realm permission policies remain unsupported and fail closed.
/// </summary>
public class ZonePermissionCheck : SpecialEffectAction
{
    internal static uint GetPublicReturnPoint(bool publicGarden, int selector, int point, int level, int gearScore)
    {
        if (!publicGarden || selector != 149 || level < 55 || gearScore < 8000)
            return 0;
        return point is 1006 or 1008 or 1009 or 1010 or 1013 ? (uint)point : 0;
    }

    internal static uint GetAuthoredDestinationZone(uint point) => point switch
    {
        1006 or 1008 or 1009 => 378,
        1010 or 1013 => 382,
        _ => 0
    };

    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
        SkillCastTarget targetObj, CastAction castObj, Skill skill, SkillObject skillObject,
        DateTime time, int value1, int value2, int value3, int value4)
    {
        if (caster is not Character character)
            return;
        var publicGarden = global::AAEmu.Game.Models.AppConfiguration.Instance.Account?.FreeGardenAccess == true;
        var point = GetPublicReturnPoint(publicGarden, value1, value2, character.Level,
            publicGarden ? character.GearScore : 0);
        var destination = point == 0 ? null : PortalManager.Instance.GetReturnDestinationById(point);
        if (value3 != 0 || value4 != 0 || destination == null ||
            destination.ZoneId != GetAuthoredDestinationZone(point))
        {
            Logger.Warn("Garden interior transfer refused: character={0}, selector={1}, point={2}, publicGarden={3}",
                character.Id, value1, value2, publicGarden);
            character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
            return;
        }

        Logger.Info("Garden interior transfer: character={0}, returnPoint={1}, zone={2}",
            character.Id, point, destination.ZoneId);
        // Return checks ZoneLoaded before any mutation and uses the existing same-world handoff.
        new Return().Execute(caster, casterObj, target, targetObj, castObj, skill, skillObject,
            time, checked((int)point), 0, 0, 0);
    }
}
