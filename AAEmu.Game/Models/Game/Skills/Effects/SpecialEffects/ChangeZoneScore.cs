using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

/// <summary>Garden's authored point-delta variant; other score modes are not promoted.</summary>
public class ChangeZoneScore : SpecialEffectAction
{
    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
        CastAction castObj, Skill skill, SkillObject skillObject, DateTime time, int value1, int value2, int value3, int value4)
    {
        if (value1 == GardenScoreGameData.Kind && value2 == 1 && value3 == 0 && target is Character player)
        {
            var before = player.GardenScore.Score;
            player.GardenScore.Add(value4);
            Logger.Info("Garden score: character={0} before={1} requestedDelta={2} after={3} level={4}",
                player.Id, before, value4, player.GardenScore.Score, player.GardenScore.Level);
        }
        else if (target is Character)
            Logger.Warn("Unsupported score mutation: kind={0} mode={1} unit={2}", value1, value2, value3);
    }
}
