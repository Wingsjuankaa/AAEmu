using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Scripts.Commands
{
    public class CombatStat : ICommand
    {
        private static readonly IReadOnlyDictionary<string, CombatStatKind> StatAliases =
            new Dictionary<string, CombatStatKind>(StringComparer.OrdinalIgnoreCase)
            {
                ["melee_accuracy"] = CombatStatKind.MeleeAccuracy,
                ["ranged_accuracy"] = CombatStatKind.RangedAccuracy,
                ["spell_accuracy"] = CombatStatKind.SpellAccuracy,
                ["melee_crit"] = CombatStatKind.MeleeCritical,
                ["ranged_crit"] = CombatStatKind.RangedCritical,
                ["spell_crit"] = CombatStatKind.SpellCritical,
                ["heal_crit"] = CombatStatKind.HealCritical,
                ["melee_parry"] = CombatStatKind.MeleeParry,
                ["ranged_parry"] = CombatStatKind.RangedParry,
                ["block"] = CombatStatKind.Block,
                ["dodge"] = CombatStatKind.Dodge
            };

        public void OnLoad()
        {
            CommandManager.Instance.Register("combatstat", this);
        }

        public string GetCommandLineHelp()
        {
            return "show [self|target] | set <stat> <1..100> [self|target] | clear <stat|all> [self|target]";
        }

        public string GetCommandHelpText()
        {
            return "Temporary, session-only combat percentage overrides for AA8 diagnostics.";
        }

        public void Execute(Character character, string[] args)
        {
            if (args.Length == 0)
            {
                SendUsage(character);
                return;
            }

            var action = args[0].ToLowerInvariant();
            switch (action)
            {
                case "show":
                    Show(character, args);
                    return;
                case "set":
                    Set(character, args);
                    return;
                case "clear":
                    Clear(character, args);
                    return;
                default:
                    SendUsage(character);
                    return;
            }
        }

        private static void Show(Character character, string[] args)
        {
            if (args.Length > 2)
            {
                SendUsage(character);
                return;
            }

            if (!TryResolveTarget(character, args.Length == 2 ? args[1] : "self", out var target))
                return;

            var service = CombatStatOverrideManager.Instance;
            var overrides = service.GetOverrides(target);
            character.SendMessage(
                "[CombatStat] {0} ({1}) - overrides are server-only and cleared on relog.",
                target.Name,
                target.ObjId);

            foreach (var alias in StatAliases.OrderBy(entry => entry.Key))
            {
                var computedValue = service.GetBaseValue(target, alias.Value);
                var nativeBonus = service.GetDirectNativeBonus(target, alias.Value);
                var baseValue = computedValue - nativeBonus;
                var effective = service.Resolve(target, alias.Value, computedValue);
                var overrideText = overrides.TryGetValue(alias.Value, out var value)
                    ? value.ToString("0.###", CultureInfo.InvariantCulture)
                    : "none";
                character.SendMessage(
                    "[CombatStat] {0}: base={1:0.###}% nativeBonus={2:+0.###;-0.###;0}% override={3} effective={4:0.###}%",
                    alias.Key,
                    baseValue,
                    nativeBonus,
                    overrideText,
                    effective);
            }

            character.SendMessage(
                "[CombatStat] The character window is client-calculated; use combat results and server traces as authority for overrides.");
        }

        private static void Set(Character character, string[] args)
        {
            if (args.Length < 3 || args.Length > 4)
            {
                SendUsage(character);
                return;
            }

            if (!StatAliases.TryGetValue(args[1], out var stat))
            {
                SendKnownStats(character);
                return;
            }

            if (!float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
                || float.IsNaN(value)
                || float.IsInfinity(value)
                || value < 1f
                || value > 100f)
            {
                character.SendMessage("[CombatStat] Value must be a finite percentage between 1 and 100.");
                return;
            }

            if (!TryResolveTarget(character, args.Length == 4 ? args[3] : "self", out var target))
                return;

            var service = CombatStatOverrideManager.Instance;
            var baseValue = service.GetBaseValue(target, stat);
            service.Set(target, stat, value);
            character.SendMessage(
                "[CombatStat] {0} on {1}: base={2:0.###}% override={3:0.###}% effective={3:0.###}%.",
                args[1].ToLowerInvariant(),
                target.Name,
                baseValue,
                value);
        }

        private static void Clear(Character character, string[] args)
        {
            if (args.Length < 2 || args.Length > 3)
            {
                SendUsage(character);
                return;
            }

            if (!TryResolveTarget(character, args.Length == 3 ? args[2] : "self", out var target))
                return;

            var service = CombatStatOverrideManager.Instance;
            if (args[1].Equals("all", StringComparison.OrdinalIgnoreCase))
            {
                service.ClearAll(target);
                character.SendMessage("[CombatStat] Cleared all overrides on {0}.", target.Name);
                return;
            }

            if (!StatAliases.TryGetValue(args[1], out var stat))
            {
                SendKnownStats(character);
                return;
            }

            var removed = service.Clear(target, stat);
            character.SendMessage(
                "[CombatStat] {0} override on {1}: {2}.",
                args[1].ToLowerInvariant(),
                target.Name,
                removed ? "cleared" : "not set");
        }

        private static bool TryResolveTarget(Character character, string selector, out Unit target)
        {
            target = character;
            if (selector.Equals("self", StringComparison.OrdinalIgnoreCase))
                return true;

            if (!selector.Equals("target", StringComparison.OrdinalIgnoreCase))
            {
                character.SendMessage("[CombatStat] Selector must be self or target.");
                return false;
            }

            if (!(character.CurrentTarget is Unit selected))
            {
                character.SendMessage("[CombatStat] No unit target selected.");
                return false;
            }

            target = selected;
            return true;
        }

        private static void SendUsage(Character character)
        {
            character.SendMessage(
                "[CombatStat] /combatstat show [self|target] | set <stat> <1..100> [self|target] | clear <stat|all> [self|target]");
        }

        private static void SendKnownStats(Character character)
        {
            character.SendMessage("[CombatStat] Known stats: {0}", string.Join(", ", StatAliases.Keys.OrderBy(name => name)));
        }
    }
}
