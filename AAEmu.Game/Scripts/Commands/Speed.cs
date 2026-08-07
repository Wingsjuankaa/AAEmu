using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Scripts.Commands
{
    public class Speed : ICommand
    {
        public void OnLoad()
        {
            string[] names = { "speed", "gm_speed", "velocidad" };
            CommandManager.Instance.Register(names, this);
        }

        public string GetCommandLineHelp()
        {
            return $"(target) <{GmSpeedLevelPolicy.MinLevel}-{GmSpeedLevelPolicy.MaxLevel}|reset>";
        }

        public string GetCommandHelpText()
        {
            return "Applies the native AA8 movement-speed modifier. Each level adds 1% speed; " +
                   "\"reset\" removes the temporary GM override.";
        }

        public void Execute(Character character, string[] args)
        {
            if (args.Length == 0)
            {
                SendUsage(character);
                return;
            }

            var target = WorldManager.Instance.GetTargetOrSelf(character, args[0], out var firstArg);
            if (args.Length <= firstArg)
            {
                SendUsage(character);
                return;
            }

            var value = args[firstArg];
            if (value.Equals("reset", StringComparison.OrdinalIgnoreCase))
            {
                if (RemoveOverride(target))
                {
                    character.SendMessage(
                        "[Speed] Restored normal speed for |cFFFFFFFF{0}|r.",
                        target.Name);
                }
                else
                {
                    character.SendMessage(
                        "[Speed] |cFFFFFFFF{0}|r has no active GM speed override.",
                        target.Name);
                }

                return;
            }

            if (!int.TryParse(value, out var level) || !GmSpeedLevelPolicy.IsValid(level))
            {
                character.SendMessage(
                    "|cFFFF0000[Speed] Allowed speed levels: {0}-{1}, or reset.|r",
                    GmSpeedLevelPolicy.MinLevel,
                    GmSpeedLevelPolicy.MaxLevel);
                return;
            }

            RemoveOverride(target);

            // Buff 3965 is also a legitimate AA8 equipment-set buff. Never
            // remove or replace an instance that this GM command did not own.
            if (target.Buffs.CheckBuff(GmSpeedLevelPolicy.NativeBuffId))
            {
                character.SendMessage(
                    "|cFFFF0000[Speed] {0} already has native buff {1}; " +
                    "the GM override was not applied.|r",
                    target.Name,
                    GmSpeedLevelPolicy.NativeBuffId);
                return;
            }

            var template = SkillManager.Instance.GetBuffTemplate(GmSpeedLevelPolicy.NativeBuffId);
            if (template == null)
            {
                character.SendMessage(
                    "|cFFFF0000[Speed] Native AA8 speed buff {0} is unavailable.|r",
                    GmSpeedLevelPolicy.NativeBuffId);
                return;
            }

            var speedBuff = new Buff(
                target,
                target,
                new SkillCasterUnit(target.ObjId),
                template,
                null,
                DateTime.UtcNow)
            {
                AbLevel = GmSpeedLevelPolicy.ToNativeAbilityLevel(level)
            };

            target.Buffs.AddBuff(speedBuff);
            target.GmSpeedBuffIndex = speedBuff.Index;

            character.SendMessage(
                "[Speed] Set |cFFFFFFFF{0}|r to level {1} (+{1}%, x{2:0.00}).",
                target.Name,
                level,
                GmSpeedLevelPolicy.ToMoveSpeedMultiplier(level));

            if (target != character)
            {
                target.SendMessage(
                    "[Speed] |cFFFFFFFF{0}|r set your speed to level {1} (+{1}%).",
                    character.Name,
                    level);
            }
        }

        private static bool RemoveOverride(Character target)
        {
            if (target.GmSpeedBuffIndex == 0)
                return false;

            var buff = target.Buffs.GetEffectByIndex(target.GmSpeedBuffIndex);
            target.GmSpeedBuffIndex = 0;
            if (buff == null)
                return false;

            buff.Exit();
            return true;
        }

        private void SendUsage(Character character)
        {
            character.SendMessage(
                "[Speed] {0}speed {1}",
                CommandManager.CommandPrefix,
                GetCommandLineHelp());
        }
    }
}
