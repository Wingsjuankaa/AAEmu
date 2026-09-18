using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.Game.Models.Game.Skills;

/// <summary>
/// A short-lived permission for the next client-requested Combo (special 48).
/// This never learns, schedules or executes a skill. Value2 is the native window
/// after combat_sync, not a delay for World to synthesize another cast.
/// </summary>
public sealed class ClientSkillCombo(TimeProvider clock = null)
{
    private readonly TimeProvider _clock = clock ?? TimeProvider.System;
    private readonly object _lock = new();
    private uint _root;
    private uint _next;
    private DateTimeOffset _expires;

    public bool CanContinue(uint skillId, Func<uint, bool> ownsRoot)
    {
        lock (_lock)
            return skillId != 0 && skillId == _next && _clock.GetUtcNow() < _expires && ownsRoot(_root);
    }

    public void Accepted(SkillTemplate template, int level, Func<uint, bool> ownsRoot)
    {
        lock (_lock)
        {
            var root = template != null && CanContinue(template.Id, ownsRoot) ? _root : template?.Id ?? 0;
            _root = _next = 0;
            _expires = default;
            if (root == 0 || !ownsRoot(root) || !TryGetUnconditionalLink(template, level, out var next, out var windowMs))
                return;
            _root = root;
            _next = next;
            // SkillComboMan r575: expiry = start + combat_sync + special.value2.
            // FireAnim carries the combat_sync_event_list.g projection already
            // used by World. Plot links without a fire animation have no offset.
            var recoveryMs = Math.Max(0, template.FireAnim?.CombatSyncTime ?? 0);
            _expires = _clock.GetUtcNow().AddMilliseconds((long)windowMs + recoveryMs);
        }
    }

    // Battlerage's r575 links are unconditional, chance 100, level 1..99.
    // Conditional links need their own evidence/evaluation; never authorize one
    // merely because a Combo row exists somewhere in the template.
    public static bool TryGetUnconditionalLink(SkillTemplate template, int level, out uint next, out int windowMs)
    {
        next = 0;
        windowMs = 0;
        // Cast-time/channelled chains require a confirmed fire edge; accepting
        // their start must not grant a child before the parent actually fires.
        if (template?.Effects == null || template.CastingTime > 0 || template.ChannelingTime > 0)
            return false;
        foreach (var effect in template.Effects)
        {
            if (effect.Template is not SpecialEffect { SpecialEffectTypeId: SpecialType.Combo, Value1: > 0, Value2: > 0 } combo)
                continue;
            if (level < effect.StartLevel || level > effect.EndLevel || effect.Chance != 100 ||
                !effect.Friendly || !effect.NonFriendly || !effect.Front || !effect.Back ||
                effect.SourceBuffTagId != 0 || effect.SourceNoBuffTagId != 0 ||
                effect.TargetBuffTagId != 0 || effect.TargetNoBuffTagId != 0 || effect.TargetNpcTagId != 0 ||
                effect.SourceBuffStackCountMin != 0 || effect.SourceBuffStackCountMax != 0 ||
                effect.TargetBuffStackCountMin != 0 || effect.TargetBuffStackCountMax != 0 ||
                effect.SourceExceptBuffStackCountMin != 0 || effect.SourceExceptBuffStackCountMax != 0 ||
                effect.TargetExceptBuffStackCountMin != 0 || effect.TargetExceptBuffStackCountMax != 0 ||
                effect.TargetCombatResourceId != 0 || effect.StartCombatResource != 0 || effect.EndCombatResource != 0 ||
                effect.StartCastingUseChance != 1 || effect.EndCastingUseChance != 100 ||
                effect.ConsumeSourceItem || effect.ConsumeItemId != 0 || effect.ItemSetId != 0 || effect.InteractionSuccessHit)
                continue;
            // Ambiguous alternatives require explicit condition handling, not first-row wins.
            if (next != 0 && (next != (uint)combo.Value1 || windowMs != combo.Value2))
                return false;
            next = (uint)combo.Value1;
            windowMs = combo.Value2;
        }
        return next != 0;
    }
}
