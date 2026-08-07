using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Plots.Tree
{
    public class PlotNode
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();
        
        // Tree
        public PlotTree Tree;
        public PlotNode Parent;
        public List<PlotNode> Children;
        // Plots
        public PlotEventTemplate Event;
        public PlotNextEvent ParentNextEvent;
        

        public PlotNode()
        {
            Children = new List<PlotNode>();
        }

        private bool IsChannelStart()
        {
            foreach(var child in Children)
            {
                if (child.ParentNextEvent.Channeling == true)
                    return true;
            }
            return false;
        }

        public int ComputeDelayMs(PlotState state, PlotTargetInfo targetInfo)
        {
            return ParentNextEvent.GetDelay(state, targetInfo, Parent);
        }
        
        public bool CheckConditions(PlotState state, PlotTargetInfo targetInfo)
        {
            return Event.Conditions.All(condition => condition.CheckCondition(state, targetInfo));
        }

        public void Execute(PlotState state, PlotTargetInfo targetInfo, CompressedGamePackets packets = null)
        {
            //_log.Debug("Executing plot node with id {0}", Event.Id);

            var stopwatch = new Stopwatch();
            stopwatch.Start();
            state.CurrentTargetCount = targetInfo.EffectedTargets.Count;
            byte flag = 2;
            foreach (var eff in Event.Effects)
            {
                try
                {
                    eff.ApplyEffect(state, targetInfo, Event, ref flag, IsChannelStart());
                }
                catch (Exception e)
                {
                    state?.Caster?.SendPacket(new SCChatMessagePacket((byte)0, Chat.ChatType.Notice, "Plot Effects Error - Check Logs"));
                    _log.Error("[Plot Effects Error]: {0}\n{1}", e.Message, e.StackTrace);
                }
            }

            NativeSkillLiveTrace.Record(
                $"plot_event_{Event.Id}",
                state.ActiveSkill,
                state.Caster,
                targetInfo.Target,
                targetInfo.EffectedTargets.Count,
                Event.Effects.Count);

            double castTime = Event.NextEvents
                 .Where(nextEvent => nextEvent.Casting || nextEvent.Channeling)
                 .Max(nextEvent => nextEvent.Delay / 10 as int?) ?? 0;
            castTime = state.Caster.ApplySkillModifiers(state.ActiveSkill, SkillAttribute.CastTime, castTime) * state.Caster.CastTimeMul;
            castTime = Math.Max(castTime, 0);

            if (castTime > 0)
                state.IsCasting = true;
            if (CompletesCastOrChannel(ParentNextEvent))
                state.IsCasting = false;

            if (Event.HasSpecialEffects() || castTime > 0 || Event.Conditions.Count > 0)
            {
                var skill = state.ActiveSkill;
                var unkId = (ParentNextEvent?.Casting ?? false) || (ParentNextEvent?.Channeling ?? false) ? state.Caster.ObjId : 0;

                PlotObject casterPlotObj;
                if (targetInfo.Source.ObjId == uint.MaxValue)
                    casterPlotObj = new PlotObject(targetInfo.Source.Transform);
                else
                    casterPlotObj = new PlotObject(targetInfo.Source);

                PlotObject targetPlotObj;
                if (targetInfo.Target.ObjId == uint.MaxValue)
                    targetPlotObj = new PlotObject(targetInfo.Target.Transform);
                else
                    targetPlotObj = new PlotObject(targetInfo.Target);

                var targetUnitIds = targetInfo.EffectedTargets
                    .Where(target => target != null && target.ObjId != uint.MaxValue)
                    .Select(target => target.ObjId)
                    .Distinct()
                    .Take(byte.MaxValue)
                    .ToArray();
                byte targetCount = (byte)targetUnitIds.Length;

                if (Event.Id is 5100 or 37731 or 37838)
                {
                    _log.Info(
                        "[AA8Movement] SCPlotEvent skill={0} tl={1} event={2} caster={3}:{4} target={5}:{6} targetCount={7} flag=0x{8:X2} inputDirection={9}",
                        skill.Template.Id, skill.TlId, Event.Id,
                        casterPlotObj.Type, casterPlotObj.UnitId,
                        targetPlotObj.Type, targetPlotObj.UnitId,
                        targetCount, flag, state.SkillObject?.InputDirection ?? 0);
                }

                var packet = new SCPlotEventPacket(skill.TlId, Event.Id, skill.Template.Id, casterPlotObj,
                    targetPlotObj, unkId, (ushort)castTime, flag, state.SkillObject?.InputDirection ?? 0, 0,
                    targetCount, targetUnitIds);

                if (packets != null)
                    packets.AddPacket(packet);
                else
                    state.Caster.BroadcastPacket(packet, true);
                
                _log.Trace($"Execute Took {stopwatch.ElapsedMilliseconds} to finish.");
            }
        }

        public static bool CompletesCastOrChannel(PlotNextEvent parentNextEvent)
        {
            return (parentNextEvent?.Casting ?? false) ||
                   (parentNextEvent?.Channeling ?? false);
        }
    }
}
