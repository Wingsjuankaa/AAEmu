using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.StaticValues;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

internal static class MechanicsSandboxServicePolicy
{
    internal static bool SupportsRole(NpcTemplate template, string role, bool questTalk)
    {
        if (template == null || template.Aggression || !template.NonPushableByActor)
            return false;
        var expected = role switch
        {
            "specializations" => SkillsEnum.ChangeSkillsets,
            "warehouse" => SkillsEnum.UseWarehouse,
            "weapons" or "armor" => SkillsEnum.UseStore,
            _ => 0u
        };
        return expected != 0 && NpcInteractionRules.PrimarySkill(template, questTalk) == expected &&
               (role is not ("weapons" or "armor") || template.MerchantPackId != 0);
    }
}
