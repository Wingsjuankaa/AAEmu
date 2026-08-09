using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Threading.Tasks;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;
using NLog;

namespace AAEmu.Game.Models.Game.Skills.Plots.Tree
{
    public class PlotTree
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();
        
        public uint PlotId { get; set; }
        
        public PlotNode RootNode { get; set; }

        public PlotTree(uint plotId)
        {
            PlotId = plotId;
        }

        public async Task Execute(PlotState state)
        {
            var treeWatch = new Stopwatch();
            treeWatch.Start();
            _log.Trace("Executing plot tree with ID {0}", PlotId);
            MechanicsRuntime.Current?.EventSink?.RecordEvent(
                "plot_started",
                state.Caster?.ObjId ?? 0,
                state.Target?.ObjId ?? 0,
                $"plot={PlotId};skill={state.ActiveSkill?.Template?.Id ?? 0};tl={state.ActiveSkill?.TlId ?? 0}");
            try
            {
                var stopWatch = new Stopwatch();
                stopWatch.Start();

                var queue = new Queue<(PlotNode node, DateTime timestamp, PlotTargetInfo targetInfo)>();
                var executeQueue = new Queue<(PlotNode node, PlotTargetInfo targetInfo)>();

                queue.Enqueue((RootNode, MechanicsRuntime.UtcNow, new PlotTargetInfo(state)));

                while (queue.Count > 0)
                {
                    var nodewatch = new Stopwatch();
                    nodewatch.Start();
                    if (state.CancellationRequested())
                    {
                        if (state.IsCasting)
                        {
                            state.Caster.BroadcastPacket(
                                new SCPlotCastingStoppedPacket(state.ActiveSkill.TlId, 0, 1),
                                true
                            );
                            state.Caster.BroadcastPacket(
                                new SCPlotChannelingStoppedPacket(state.ActiveSkill.TlId, 0, 1),
                                true
                            );
                        }

                        DoPlotEnd(state);
                        return;
                    }
                    var item = queue.Dequeue();
                    var now = MechanicsRuntime.UtcNow;
                    var node = item.node;
                    var releasedCast = state.ShouldRelease(node.ParentNextEvent);

                    if (now >= item.timestamp || releasedCast)
                    {
                        state.CompleteCasting(node.ParentNextEvent, releasedCast);
                        if (state.Tickets.ContainsKey(node.Event.Id))
                            state.Tickets[node.Event.Id]++;
                        else
                            state.Tickets.TryAdd(node.Event.Id, 1);

                        //Check if we hit max tickets
                        if (state.Tickets[node.Event.Id] > node.Event.Tickets
                            && node.Event.Tickets > 1)
                        {
                            continue;
                        }

                        item.targetInfo.UpdateTargetInfo(node.Event, state);

                        if (item.targetInfo.Target == null)
                            continue;

                        var condition = node.CheckConditions(state, item.targetInfo);

                        if (condition)
                        {
                            executeQueue.Enqueue((node, item.targetInfo));

                            // Plot effects are part of the current event and must be
                            // visible to zero-delay child conditions. Delaying this
                            // flush until the scheduler reaches a future timestamp
                            // made effect-driven branches read stale PlotState values
                            // (for example, Targets assigned by SetVariable).
                            FlushExecutionQueue(executeQueue, state);
                        }
                        
                        var eligibleChildren = node.Children
                            .Where(child => condition != child.ParentNextEvent.Fail)
                            .ToList();
                        var totalWeight = GetTotalNextEventWeight(eligibleChildren);
                        var selectedChildren = SelectNextChildrenByWeight(
                            eligibleChildren,
                            totalWeight > 0 ? Rand.Next(0, totalWeight) : 0);

                        foreach (var child in selectedChildren)
                        {
                            if (child?.ParentNextEvent?.PerTarget ?? false)
                            {
                                foreach(var target in item.targetInfo.EffectedTargets)
                                {
                                    var targetInfo = new PlotTargetInfo(item.targetInfo.Source, target);
                                    var delayMs = child.ComputeDelayMs(state, targetInfo);
                                    state.BeginCasting(child.ParentNextEvent, delayMs, now);
                                    queue.Enqueue(
                                        (
                                        child,
                                        now.AddMilliseconds(delayMs),
                                        targetInfo
                                        )
                                    );
                                }
                            }
                            else
                            {
                                var targetInfo = new PlotTargetInfo(item.targetInfo.Source, item.targetInfo.Target);
                                var delayMs = child.ComputeDelayMs(state, targetInfo);
                                state.BeginCasting(child.ParentNextEvent, delayMs, now);
                                queue.Enqueue(
                                    (
                                    child,
                                    now.AddMilliseconds(delayMs),
                                    targetInfo
                                    )
                                );
                            }
                        }
                    }
                    else
                    {
                        queue.Enqueue((node, item.timestamp, item.targetInfo));
                        FlushExecutionQueue(executeQueue, state);
                    }

                    if (queue.Count > 0)
                    {
                        int delay = (int)queue.Min(o => (o.timestamp - MechanicsRuntime.UtcNow).TotalMilliseconds);
                        delay = Math.Max(delay, 0);

                        //await Task.Delay(delay).ConfigureAwait(false);
                        if (delay > 0)
                            await MechanicsRuntime.Delay(TimeSpan.FromMilliseconds(Math.Min(delay, 15)))
                                .ConfigureAwait(false);
                        
                    }

                    if (nodewatch.ElapsedMilliseconds > 100)
                        _log.Trace($"Event:{node.Event.Id} Took {nodewatch.ElapsedMilliseconds} to finish.");
                }

                FlushExecutionQueue(executeQueue, state);
            } catch (Exception e)
            {
                MechanicsRuntime.Current?.ExceptionSink?.RecordException("plot_tree", e);
                _log.Error($"Main Loop Error: {e.Message}\n {e.StackTrace}");
            }
            
            DoPlotEnd(state);
            _log.Trace("Tree with ID {0} has finished executing took {1}ms", PlotId, treeWatch.ElapsedMilliseconds);
        }

        public static int GetTotalNextEventWeight(IEnumerable<PlotNode> children)
        {
            if (children == null)
                return 0;

            long total = 0;
            foreach (var child in children)
            {
                var weight = child?.ParentNextEvent?.Weight ?? 0;
                if (weight <= 0)
                    continue;
                total += weight;
                if (total >= int.MaxValue)
                    return int.MaxValue;
            }

            return (int)total;
        }

        /// <summary>
        /// Native plot-next weights form one relative-weight choice while
        /// weight-zero edges remain unconditional. AA8 Rain of Fire therefore
        /// selects either its normal 95-weight impact or its five-times-damage
        /// 5-weight impact, never both.
        /// </summary>
        public static IReadOnlyList<PlotNode> SelectNextChildrenByWeight(
            IEnumerable<PlotNode> children,
            int roll)
        {
            var materialized = children?.Where(child => child != null).ToList()
                               ?? new List<PlotNode>();
            var totalWeight = GetTotalNextEventWeight(materialized);
            if (totalWeight <= 0)
                return materialized;

            var normalizedRoll = (int)(((long)roll % totalWeight + totalWeight) % totalWeight);
            PlotNode selected = null;
            var cursor = 0;
            foreach (var child in materialized)
            {
                var weight = child.ParentNextEvent?.Weight ?? 0;
                if (weight <= 0)
                    continue;
                cursor += weight;
                if (normalizedRoll < cursor)
                {
                    selected = child;
                    break;
                }
            }

            return materialized
                .Where(child => (child.ParentNextEvent?.Weight ?? 0) <= 0 ||
                                ReferenceEquals(child, selected))
                .ToList();
        }
        
        private void FlushExecutionQueue(Queue<(PlotNode node, PlotTargetInfo targetInfo)> executeQueue, PlotState state)
        { 
            var packets = new CompressedGamePackets();
            while (executeQueue.Count > 0)
            {
                var item = executeQueue.Dequeue();
                item.node.Execute(state, item.targetInfo, packets);
            }
            
            if (packets.Packets.Count > 0)
                state.Caster.BroadcastPacket(packets, true);
        }

        private void EndPlotChannel(PlotState state)
        {
            foreach(var pair in state.ChanneledBuffs)
            {
                pair.unit.Buffs.RemoveBuff(pair.buffId);
            }
        }

        private void DoPlotEnd(PlotState state)
        {
            state.Caster?.BroadcastPacket(new SCPlotEndedPacket(state.ActiveSkill.TlId), true);
            EndPlotChannel(state);

            state.Caster.Cooldowns.AddCooldown(state.ActiveSkill.Template.Id, (uint)state.ActiveSkill.Template.CooldownTime);

            if (state.Caster is Character character && character.IgnoreSkillCooldowns)
                character.ResetSkillCooldown(state.ActiveSkill.Template.Id, false);

            //Maybe always do thsi on end of plot?
            //Should we check if it was a channeled skill?
            if (state.CancellationRequested())
                state.Caster.Events.OnChannelingCancel(state.ActiveSkill, new OnChannelingCancelArgs { });

            NativeSkillLiveTrace.Record(
                "plot_ended",
                state.ActiveSkill,
                state.Caster,
                state.ActiveSkill.InitialTarget,
                cancelled: state.CancellationRequested());
            MechanicsRuntime.Current?.EventSink?.RecordEvent(
                "plot_ended",
                state.Caster?.ObjId ?? 0,
                state.Target?.ObjId ?? 0,
                $"plot={PlotId};skill={state.ActiveSkill?.Template?.Id ?? 0};tl={state.ActiveSkill?.TlId ?? 0};cancelled={state.CancellationRequested()}");
            SkillManager.Instance.ReleaseId(state.ActiveSkill.TlId);
            
            state.Caster?.OnSkillEnd(state.ActiveSkill);
            state.ActiveSkill.Callback?.Invoke();
            if (state.Caster?.ActivePlotState == state)
                state.Caster.ActivePlotState = null;
        }
    }
}
