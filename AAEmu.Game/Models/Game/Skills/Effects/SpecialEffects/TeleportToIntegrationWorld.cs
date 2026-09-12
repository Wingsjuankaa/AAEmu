using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>Routes the Garden entrance/exit within this local realm using authored Return points.</summary>
public class TeleportToIntegrationWorld : SpecialEffectAction
{
    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target,
        SkillCastTarget targetObj, CastAction castObj, Skill skill, SkillObject skillObject,
        DateTime time, int value1, int value2, int value3, int value4)
    {
        if (caster is not Character character)
            return;
        var point = PortalManager.Instance.GetIntegrationReturnPoint(value1);
        if (point == 0 || PortalManager.Instance.GetReturnDestinationById(point) == null)
        {
            Logger.Warn("Integration return destination unavailable: direction={0}, point={1}", value1, point);
            character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
            return;
        }

        Logger.Info("Garden transfer: character={0}, direction={1}, returnPoint={2}", character.Id, value1, point);
        new Return().Execute(caster, casterObj, target, targetObj, castObj, skill, skillObject,
            time, checked((int)point), 0, 0, 0);
    }
}
