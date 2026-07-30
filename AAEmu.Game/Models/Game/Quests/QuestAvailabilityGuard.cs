using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests
{
    /// <summary>
    /// Enforces the native quest_context level and race bounds when a client
    /// requests a quest. AA8 stores race as a bit mask in race enum order.
    /// </summary>
    public static class QuestAvailabilityGuard
    {
        private const byte AllRaces = byte.MaxValue;

        public static bool CanAccept(
            QuestTemplate template,
            Character character,
            out string reason)
        {
            if (template == null || character == null)
            {
                reason = "missing_quest_or_character";
                return false;
            }

            return Evaluate(
                character.Level,
                (byte)character.Race,
                template.MinLevel,
                template.MaxLevel,
                template.RaceMask,
                out reason);
        }

        public static bool Evaluate(
            byte characterLevel,
            byte characterRace,
            byte minLevel,
            byte maxLevel,
            byte raceMask,
            out string reason)
        {
            reason = string.Empty;
            if (minLevel > 0 && characterLevel < minLevel)
            {
                reason = "below_min_level";
                return false;
            }
            if (maxLevel > 0 && characterLevel > maxLevel)
            {
                reason = "above_max_level";
                return false;
            }
            if (raceMask == 0 || raceMask == AllRaces)
                return true;
            if (characterRace == 0 || characterRace > 8)
            {
                reason = "invalid_character_race";
                return false;
            }

            var characterRaceMask = 1 << (characterRace - 1);
            if ((raceMask & characterRaceMask) != 0)
                return true;

            reason = "race_not_allowed";
            return false;
        }
    }
}
