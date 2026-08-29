using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Features;
using AAEmu.Game.Models.Game.Housing;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class RebuildHousing : SpecialEffectAction
{
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
        if (FeaturesManager.Fsets?.Check(Feature.rebuildHouse) != true)
        {
            skill.Cancelled = true;
            return;
        }

        if (caster is not Character character ||
            target is not House house ||
            skillObject is not SkillObjectHousingRebuilding rebuilding)
        {
            skill.Cancelled = true;
            return;
        }

        if (rebuilding.TargetHousingId == 0)
        {
            skill.Cancelled = true;
            return;
        }

        if (HousingManager.Instance.TryRebuildHouse(character, house, rebuilding.TargetHousingId, skill.Template.Id, out var failure))
            return;

        skill.Cancelled = true;
        character.SendErrorMessage(failure.Reason switch
        {
            HousingRebuildBlockReason.MissingMaterials => ErrorMessageType.CraftMaterialRequired,
            HousingRebuildBlockReason.MissingLabor => ErrorMessageType.NotEnoughLaborPower,
            HousingRebuildBlockReason.MissingActability => ErrorMessageType.ActabilityNotEnoughPoint,
            HousingRebuildBlockReason.MissingTaxPayment => ErrorMessageType.MailNotEnoughMoneyToPayTaxes,
            HousingRebuildBlockReason.NotOwner => ErrorMessageType.NoPermissionToLoot,
            _ => ErrorMessageType.InvalidHouseInfo
        });

        Logger.Warn("Housing rebuild rejected: character={0}, house={1}, targetHousing={2}, reason={3}",
            character.Id, house.Id, rebuilding.TargetHousingId, failure.Reason);
    }
}
