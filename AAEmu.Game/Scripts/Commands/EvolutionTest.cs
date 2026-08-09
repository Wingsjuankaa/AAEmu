using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Scripts.Commands
{
    public class EvolutionTest : ICommand
    {
        public void OnLoad()
        {
            CommandManager.Instance.Register("evolutiontest", this);
        }

        public string GetCommandLineHelp()
        {
            return "mode <natural|success|fail|crystallize|bonusxp> | clear";
        }

        public string GetCommandHelpText()
        {
            return "Session-only AA8 synthesis/awakening resolution controls.";
        }

        public void Execute(Character character, string[] args)
        {
            if (character.AccessLevel < 100)
            {
                character.SendMessage("[EvolutionTest] GM level 100 is required.");
                return;
            }

            if (args.Length == 1 &&
                args[0].Equals("clear", StringComparison.OrdinalIgnoreCase))
            {
                EvolutionTestModeManager.Instance.Clear(character);
                character.SendMessage("[EvolutionTest] mode=natural (cleared)");
                return;
            }

            if (args.Length != 2 ||
                !args[0].Equals("mode", StringComparison.OrdinalIgnoreCase) ||
                !TryParseMode(args[1], out var mode))
            {
                character.SendMessage(
                    "[EvolutionTest] /evolutiontest mode <natural|success|fail|crystallize|bonusxp> | clear");
                return;
            }

            EvolutionTestModeManager.Instance.Set(character, mode);
            character.SendMessage(
                "[EvolutionTest] mode={0}; requirements, costs and inheritance remain native AA8.",
                mode);
        }

        private static bool TryParseMode(
            string value,
            out EvolutionTestMode mode)
        {
            switch (value?.ToLowerInvariant())
            {
                case "natural":
                    mode = EvolutionTestMode.Natural;
                    return true;
                case "success":
                    mode = EvolutionTestMode.Success;
                    return true;
                case "fail":
                    mode = EvolutionTestMode.Fail;
                    return true;
                case "crystallize":
                    mode = EvolutionTestMode.Crystallize;
                    return true;
                case "bonusxp":
                    mode = EvolutionTestMode.BonusExperience;
                    return true;
                default:
                    mode = EvolutionTestMode.Natural;
                    return false;
            }
        }
    }
}
