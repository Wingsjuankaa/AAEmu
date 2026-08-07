using System;
using System.Collections.Generic;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Plots.Type;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Plots
{
    public class PlotEventEffect
    {
        public int Position { get; set; }
        public PlotEffectSource SourceId { get; set; }
        public PlotEffectTarget TargetId { get; set; }
        public uint ActualId { get; set; }
        public string ActualType { get; set; }

        public IEnumerable<BaseUnit> ResolveEffectTargets(PlotState state, PlotTargetInfo targetInfo)
        {
            switch (TargetId)
            {
                case PlotEffectTarget.OriginalSource:
                    if (state.Caster != null)
                        yield return state.Caster;
                    yield break;
                case PlotEffectTarget.OriginalTarget:
                    if (state.Target != null)
                        yield return state.Target;
                    yield break;
                case PlotEffectTarget.Source:
                    if (targetInfo.Source != null)
                        yield return targetInfo.Source;
                    yield break;
                case PlotEffectTarget.Target:
                    foreach (var target in targetInfo.EffectedTargets)
                        yield return target;
                    yield break;
                case PlotEffectTarget.Location:
                    // A location is the single synthetic positional target
                    // produced by the plot event. It must not depend on, or be
                    // repeated for, the units selected by the area query.
                    if (targetInfo.Target != null)
                        yield return targetInfo.Target;
                    yield break;
                default:
                    throw new InvalidOperationException("This can't happen");
            }
        }
        
        public void ApplyEffect(PlotState state, PlotTargetInfo targetInfo, PlotEventTemplate evt, ref byte flag, bool channeled = false, CompressedGamePackets gamePackets = null)
        {
            var template = SkillManager.Instance.GetEffectTemplate(ActualId, ActualType);

            var buffEffect = template as BuffEffect;
            if (buffEffect != null)
                flag = 6; //idk what this does?  

            Unit source;
            switch (SourceId)
            {
                case PlotEffectSource.OriginalSource:
                    source = state.Caster;
                    break;
                case PlotEffectSource.OriginalTarget:
                    source = state.Target as Unit;
                    break;
                case PlotEffectSource.Source:
                    source = targetInfo.Source as Unit;
                    break;
                case PlotEffectSource.Target:
                    source = targetInfo.Target as Unit;
                    break;
                default:
                    throw new InvalidOperationException("This can't happen");
            }
            
            foreach (var target in ResolveEffectTargets(state, targetInfo))
            {
                if (channeled && buffEffect != null)
                    state.ChanneledBuffs.Add((target, buffEffect.BuffId));

                template.Apply(
                    source,
                    state.CasterCaster,
                    target,
                    state.TargetCaster,
                    new CastPlot(evt.PlotId, state.ActiveSkill.TlId, evt.Id,
                        state.ActiveSkill.Template.Id, evt.AoeDiminishing,
                        state.AoeDiminishingContext),
                    new EffectSource(state.ActiveSkill), 
                    state.SkillObject,
                    DateTime.UtcNow,
                    gamePackets);
            }
        }
    }
}
