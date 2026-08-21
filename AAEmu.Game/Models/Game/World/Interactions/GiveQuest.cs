using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.World.Interactions;

public class GiveQuest : IWorldInteraction
{
    public void Execute(BaseUnit caster, SkillCaster casterType, BaseUnit target, SkillCastTarget targetType,
        uint skillId, uint doodadId, DoodadFuncTemplate objectFunc = null)
    {
        if (target is not Doodad doodad || caster is not global::AAEmu.Game.Models.Game.Char.Character character) { return; }

        doodad.UseQuest(character, skillId,
            global::AAEmu.Game.Models.Game.DoodadObj.Funcs.DoodadFuncQuest.OfferQuestKind);
    }
}
