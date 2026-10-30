using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.MechanicsSandbox;

/// <summary>
/// Sandbox-only baseline: original non-passive state plus the CURRENT skill book's passives.
/// A passive's Started BuffEffect children are ordinary Buff instances (Passive=false), so merely
/// removing snapshots tagged Passive would resurrect old trees and duplicate their child effects.
/// This object is used only by the sandbox manager, inside its retired-epoch mutation fence.
/// </summary>
internal sealed class MechanicsSandboxPassiveBaseline
{
    private readonly Character _owner;
    private readonly MechanicsSandboxBuffSnapshot[] _original;
    private readonly HashSet<uint> _originalPassiveClosure;

    private MechanicsSandboxPassiveBaseline(Character owner, MechanicsSandboxBuffSnapshot[] original,
        HashSet<uint> originalPassiveClosure)
    {
        _owner = owner;
        _original = original;
        _originalPassiveClosure = originalPassiveClosure;
    }

    public static MechanicsSandboxPassiveBaseline Capture(Character owner, IEnumerable<Buff> initialBuffs)
    {
        ArgumentNullException.ThrowIfNull(owner);
        var initial = initialBuffs.ToArray();
        if (initial.Any(buff => buff.ZoneAuthored))
            throw new InvalidOperationException("El baseline contiene buffs administrados por Zone.");
        RequireTrackedPassives(owner, initial);
        var roots = CurrentPassives(owner).Select(p => p.Template.BuffId)
            .Concat(initial.Where(buff => buff.Passive).Select(buff => buff.Template.Id));
        var closure = PassiveClosure(roots);
        return new(owner, initial.Where(buff => !buff.Passive && !closure.Contains(buff.Template.Id))
            .Select(MechanicsSandboxBuffSnapshot.Capture).ToArray(), closure);
    }

    /// <summary>Preflight this before retiring an attempt; Restore repeats it before any mutation.</summary>
    public void Validate(Character owner) => Plan(owner);

    /// <summary>
    /// Replaces RestoreBuffs, after the manager has retired old callbacks and entered Scope.Mutate.
    /// Does not capture newly cast/transient effects, refund costs, learn skills or alter ability slots.
    /// </summary>
    public void Restore(Character owner, MechanicsSandboxExecution.Scope restoration)
    {
        if (restoration?.IsMutationThread != true)
            throw new InvalidOperationException("La restauración requiere la mutación exclusiva del sandbox.");
        var (passives, baseline) = Plan(owner);
        if (owner.Buffs is not Buffs buffs)
            throw new InvalidOperationException("El sandbox requiere el consumidor de buffs real.");

        // Keep the real passive removal/apply path, including its modifiers and Started triggers.
        foreach (var passive in passives)
            passive.Remove(owner);
        foreach (var buff in AllBuffs(owner))
            buff.Exit();
        foreach (var snapshot in baseline)
        {
            var template = SkillManager.Instance.GetBuffTemplate(snapshot.TemplateId);
            buffs.RestoreMechanicsSnapshot(snapshot.Create(owner, template), snapshot.EffectiveDuration, restoration);
        }
        foreach (var passive in passives)
            passive.Apply(owner);
    }

    private (PassiveBuff[] Passives, MechanicsSandboxBuffSnapshot[] Baseline) Plan(Character owner)
    {
        if (!ReferenceEquals(owner, _owner))
            throw new InvalidOperationException("El baseline pertenece a otra sesión del personaje.");
        if (AllBuffs(owner).Any(buff => buff.ZoneAuthored))
            throw new InvalidOperationException("No se pueden restaurar buffs administrados por Zone.");
        RequireTrackedPassives(owner, AllBuffs(owner));
        var passives = CurrentPassives(owner);
        var excluded = PassiveClosure(passives.Select(p => p.Template.BuffId));
        excluded.UnionWith(_originalPassiveClosure);
        var baseline = _original.Where(snapshot => !excluded.Contains(snapshot.TemplateId)).ToArray();
        if (baseline.Any(snapshot => SkillManager.Instance.GetBuffTemplate(snapshot.TemplateId) == null))
            throw new InvalidOperationException("Falta un template del baseline original.");
        return (passives, baseline);
    }

    private static PassiveBuff[] CurrentPassives(Character owner) => owner.Skills?.PassiveBuffs.Values
        .Where(passive => passive?.Template != null &&
            (passive.Template.AbilityId == AbilityType.General ||
             passive.Template.AbilityId == owner.Ability1 || passive.Template.AbilityId == owner.Ability2 ||
             passive.Template.AbilityId == owner.Ability3))
        .OrderBy(passive => passive.Id).ToArray() ?? [];

    private static void RequireTrackedPassives(Character owner, IEnumerable<Buff> live)
    {
        var tracked = CurrentPassives(owner).Select(passive => passive.Template.BuffId).ToHashSet();
        var unknown = live.FirstOrDefault(buff => buff.Passive && !tracked.Contains(buff.Template.Id));
        if (unknown != null)
            throw new InvalidOperationException($"Pasivo {unknown.Template.Id}: productor fuera del libro actual requiere clausura adicional.");
    }

    private static Buff[] AllBuffs(Unit owner)
    {
        List<Buff> good = [], bad = [], hidden = [];
        owner.Buffs.GetAllBuffs(good, bad, hidden, true);
        return good.Concat(bad).Concat(hidden).Distinct().ToArray();
    }

    private static HashSet<uint> PassiveClosure(IEnumerable<uint> roots)
    {
        HashSet<uint> result = [], visiting = [];
        void Visit(uint id)
        {
            if (visiting.Contains(id))
                throw new InvalidOperationException($"Ciclo de buffs pasivos {id}; restauración no admitida.");
            if (!result.Add(id))
                return;
            if (result.Count > 512)
                throw new InvalidOperationException("Clausura de buffs pasivos fuera del límite del sandbox.");
            var template = SkillManager.Instance.GetBuffTemplate(id);
            if (template == null)
                return; // Missing retail passive templates are inert in PassiveBuff.Apply too.
            if (template.AuraSlaveBuffId != 0 || template.TransformBuffId != 0)
                throw new InvalidOperationException($"Pasivo {id}: aura/transform requiere clausura adicional.");
            visiting.Add(id);
            foreach (var trigger in SkillManager.Instance.GetBuffTriggerTemplates(id))
            {
                // All direct owner BuffEffects are excluded, including combat procs already present
                // at begin. Only real Started consumers re-create their children during restoration.
                if (trigger.Effect is BuffEffect effect)
                {
                    if (trigger.TargetAgentId != BuffTriggerAgent.Owner)
                        throw new InvalidOperationException($"Pasivo {id}: {trigger.Kind} con destino externo no admitido.");
                    if (effect.BuffId != 0)
                        Visit(effect.BuffId);
                }
                else if (trigger.Effect != null)
                    throw new InvalidOperationException($"Pasivo {id}: {trigger.Kind} {trigger.Effect.GetType().Name} requiere clausura adicional.");
            }
            visiting.Remove(id);
        }
        foreach (var root in roots)
            Visit(root);
        return result;
    }
}
