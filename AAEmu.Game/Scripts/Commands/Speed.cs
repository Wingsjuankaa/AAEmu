using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Utils.Scripts;

namespace AAEmu.Game.Scripts.Commands;

public class Speed : ICommand
{
    public string[] CommandNames { get; set; } = ["speed", "gm_speed", "velocidad"];

    public void OnLoad()
    {
        CommandManager.Instance.Register(CommandNames, this);
    }

    public string GetCommandLineHelp()
    {
        return $"[character_name] <{GmSpeedLevelPolicy.MinLevel}-{GmSpeedLevelPolicy.MaxLevel}|reset>";
    }

    public string GetCommandHelpText()
    {
        return "Applies the native AA10 movement-speed modifier. Each level adds 1% speed; " +
               "reset removes only the temporary override owned by this command.";
    }

    public void Execute(Character character, string[] args, IMessageOutput messageOutput)
    {
        if (args.Length is < 1 or > 2)
        {
            CommandManager.SendDefaultHelpText(this, messageOutput);
            return;
        }

        var target = character;
        var valueIndex = 0;
        if (args.Length == 2)
        {
            target = WorldManager.Instance.GetCharacter(args[0]);
            if (target == null)
            {
                CommandManager.SendErrorText(this, messageOutput, $"Online character not found: {args[0]}");
                return;
            }

            valueIndex = 1;
        }

        var value = args[valueIndex];
        if (value.Equals("reset", StringComparison.OrdinalIgnoreCase))
        {
            var removed = RemoveOverride(target);
            CommandManager.SendNormalText(this, messageOutput, removed
                ? $"Restored normal speed for {target.Name}."
                : $"{target.Name} has no active GM speed override.");
            return;
        }

        if (!int.TryParse(value, out var level) || !GmSpeedLevelPolicy.IsValid(level))
        {
            CommandManager.SendErrorText(this, messageOutput,
                $"Allowed speed levels: {GmSpeedLevelPolicy.MinLevel}-{GmSpeedLevelPolicy.MaxLevel}, or reset.");
            return;
        }

        RemoveOverride(target);

        // Buff 3965 is also a legitimate equipment-set buff. Never replace an instance
        // this command does not own.
        if (target.Buffs.CheckBuff(GmSpeedLevelPolicy.NativeBuffId))
        {
            CommandManager.SendErrorText(this, messageOutput,
                $"{target.Name} already has native speed buff {GmSpeedLevelPolicy.NativeBuffId}; override not applied.");
            return;
        }

        var template = SkillManager.Instance.GetBuffTemplate(GmSpeedLevelPolicy.NativeBuffId);
        if (template == null)
        {
            CommandManager.SendErrorText(this, messageOutput,
                $"Native AA10 speed buff {GmSpeedLevelPolicy.NativeBuffId} is unavailable.");
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

        CommandManager.SendNormalText(this, messageOutput,
            $"Set {target.Name} to level {level} (+{level}%, x{GmSpeedLevelPolicy.ToMoveSpeedMultiplier(level):0.00}).");
        if (target != character)
            target.SendMessage($"[Speed] {character.Name} set your movement speed to level {level} (+{level}%).");
    }

    private static bool RemoveOverride(Character target)
    {
        if (target.GmSpeedBuffIndex == 0)
            return false;

        var buff = target.Buffs.GetEffectByIndex(target.GmSpeedBuffIndex);
        target.GmSpeedBuffIndex = 0;
        if (buff == null || buff.Template?.BuffId != GmSpeedLevelPolicy.NativeBuffId)
            return false;

        buff.Exit();
        return true;
    }
}
