using System.Collections.Concurrent;

using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Managers
{
    public enum EvolutionTestMode
    {
        Natural = 0,
        Success,
        Fail,
        Crystallize,
        BonusExperience
    }

    /// <summary>
    /// Session-only resolution override for native AA8 evolution diagnostics.
    /// It never changes requirements, prices, compact rows or persisted odds.
    /// </summary>
    public class EvolutionTestModeManager : Singleton<EvolutionTestModeManager>
    {
        private readonly ConcurrentDictionary<uint, EvolutionTestMode> _modes =
            new ConcurrentDictionary<uint, EvolutionTestMode>();

        public EvolutionTestMode Get(Character character)
        {
            return character != null &&
                   _modes.TryGetValue(character.ObjId, out var mode)
                ? mode
                : EvolutionTestMode.Natural;
        }

        public void Set(Character character, EvolutionTestMode mode)
        {
            if (character == null)
                return;
            if (mode == EvolutionTestMode.Natural)
                _modes.TryRemove(character.ObjId, out _);
            else
                _modes[character.ObjId] = mode;
        }

        public void Clear(Character character)
        {
            if (character != null)
                _modes.TryRemove(character.ObjId, out _);
        }
    }
}
