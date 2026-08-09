using System;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Mechanics;

namespace AAEmu.Game.Models.Game.Units
{
    public enum CooldownSelectorKind
    {
        Skill,
        Tag
    }

    public readonly struct CooldownSelector
    {
        public CooldownSelectorKind Kind { get; }
        public uint Id { get; }

        private CooldownSelector(CooldownSelectorKind kind, uint id)
        {
            Kind = kind;
            Id = id;
        }

        public static CooldownSelector Skill(uint skillId) =>
            new CooldownSelector(CooldownSelectorKind.Skill, skillId);

        public static CooldownSelector Tag(uint tagId) =>
            new CooldownSelector(CooldownSelectorKind.Tag, tagId);
    }

    public sealed class CooldownDeltaEntry
    {
        public uint SkillId { get; set; }
        public int PreviousMilliseconds { get; set; }
        public int RemainingMilliseconds { get; set; }
        public bool Expired { get; set; }
    }

    public sealed class CooldownDeltaResult
    {
        public CooldownSelector Selector { get; set; }
        public IReadOnlyList<CooldownDeltaEntry> Entries { get; set; } =
            Array.Empty<CooldownDeltaEntry>();
        public bool IsNoOp => Entries.Count == 0;
    }

    public sealed class CooldownSnapshotEntry
    {
        public uint SkillId { get; set; }
        public int DurationMilliseconds { get; set; }
        public int RemainingMilliseconds { get; set; }
    }

    public class UnitCooldowns
    {
        private sealed class CooldownState
        {
            public DateTime EndTime { get; set; }
            public int DurationMilliseconds { get; set; }
            public uint CastToken { get; set; }
        }

        private readonly object _sync = new object();
        private readonly Dictionary<uint, CooldownState> _cooldowns =
            new Dictionary<uint, CooldownState>();

        // Compatibility view for legacy diagnostics. Mutations must go through
        // the explicit operations below.
        public Dictionary<uint, DateTime> Cooldowns
        {
            get
            {
                lock (_sync)
                    return _cooldowns.ToDictionary(pair => pair.Key, pair => pair.Value.EndTime);
            }
        }

        public bool StartCooldown(uint skillId, uint duration, uint castToken)
        {
            var now = MechanicsRuntime.UtcNow;
            lock (_sync)
            {
                if (_cooldowns.TryGetValue(skillId, out var current) &&
                    current.EndTime > now &&
                    current.CastToken == castToken)
                    return false;

                var durationMs = duration > int.MaxValue ? int.MaxValue : (int)duration;
                if (durationMs <= 0)
                {
                    _cooldowns.Remove(skillId);
                    return false;
                }

                _cooldowns[skillId] = new CooldownState
                {
                    EndTime = now.AddMilliseconds(durationMs),
                    DurationMilliseconds = durationMs,
                    CastToken = castToken
                };
                return true;
            }
        }

        public void AddCooldown(uint skillId, uint duration)
        {
            var now = MechanicsRuntime.UtcNow;
            lock (_sync)
            {
                if (_cooldowns.TryGetValue(skillId, out var current) && current.EndTime > now)
                    return;
            }
            StartCooldown(skillId, duration, 0);
        }

        public int GetRemaining(uint skillId, DateTime now)
        {
            lock (_sync)
            {
                if (!_cooldowns.TryGetValue(skillId, out var state))
                    return 0;

                var remaining = RemainingMilliseconds(state.EndTime, now);
                if (remaining > 0)
                    return remaining;

                _cooldowns.Remove(skillId);
                return 0;
            }
        }

        public int GetRemaining(uint skillId) => GetRemaining(skillId, MechanicsRuntime.UtcNow);

        public CooldownDeltaResult ReduceCooldown(
            CooldownSelector selector,
            int flatMilliseconds,
            int percent)
        {
            var now = MechanicsRuntime.UtcNow;
            var skillIds = ResolveSkillIds(selector);
            var entries = new List<CooldownDeltaEntry>();

            lock (_sync)
            {
                foreach (var skillId in skillIds.Distinct())
                {
                    if (!_cooldowns.TryGetValue(skillId, out var state))
                        continue;

                    var previous = RemainingMilliseconds(state.EndTime, now);
                    if (previous <= 0)
                    {
                        _cooldowns.Remove(skillId);
                        continue;
                    }

                    var percentReduction = (long)previous * Math.Max(0, percent) / 100L;
                    var reduction = Math.Max(0L, flatMilliseconds) + percentReduction;
                    var remaining = (int)Math.Max(0L, previous - reduction);
                    if (remaining == previous)
                        continue;

                    if (remaining == 0)
                        _cooldowns.Remove(skillId);
                    else
                        state.EndTime = now.AddMilliseconds(remaining);

                    entries.Add(new CooldownDeltaEntry
                    {
                        SkillId = skillId,
                        PreviousMilliseconds = previous,
                        RemainingMilliseconds = remaining,
                        Expired = remaining == 0
                    });
                }
            }

            return new CooldownDeltaResult {Selector = selector, Entries = entries};
        }

        public CooldownDeltaResult ResetCooldown(CooldownSelector selector)
        {
            var now = MechanicsRuntime.UtcNow;
            var entries = new List<CooldownDeltaEntry>();
            lock (_sync)
            {
                foreach (var skillId in ResolveSkillIds(selector).Distinct())
                {
                    if (!_cooldowns.TryGetValue(skillId, out var state))
                        continue;

                    var previous = RemainingMilliseconds(state.EndTime, now);
                    _cooldowns.Remove(skillId);
                    if (previous > 0)
                    {
                        entries.Add(new CooldownDeltaEntry
                        {
                            SkillId = skillId,
                            PreviousMilliseconds = previous,
                            RemainingMilliseconds = 0,
                            Expired = true
                        });
                    }
                }
            }
            return new CooldownDeltaResult {Selector = selector, Entries = entries};
        }

        public bool CheckCooldown(uint skillId) => GetRemaining(skillId) > 0;

        public void RemoveCooldown(uint skillId) => ResetCooldown(CooldownSelector.Skill(skillId));

        public IReadOnlyList<CooldownSnapshotEntry> GetSnapshot(DateTime now, int limit = 150)
        {
            var result = new List<CooldownSnapshotEntry>();
            lock (_sync)
            {
                foreach (var pair in _cooldowns.OrderBy(pair => pair.Key).ToList())
                {
                    var remaining = RemainingMilliseconds(pair.Value.EndTime, now);
                    if (remaining <= 0)
                    {
                        _cooldowns.Remove(pair.Key);
                        continue;
                    }

                    if (result.Count < limit)
                    {
                        result.Add(new CooldownSnapshotEntry
                        {
                            SkillId = pair.Key,
                            DurationMilliseconds = pair.Value.DurationMilliseconds,
                            RemainingMilliseconds = remaining
                        });
                    }
                }
            }
            return result;
        }

        private static IEnumerable<uint> ResolveSkillIds(CooldownSelector selector)
        {
            if (selector.Kind == CooldownSelectorKind.Skill)
                return new[] {selector.Id};
            return SkillManager.Instance.GetSkillsByTag(selector.Id) ?? new List<uint>();
        }

        private static int RemainingMilliseconds(DateTime endTime, DateTime now)
        {
            var milliseconds = (long)Math.Ceiling((endTime - now).TotalMilliseconds);
            return milliseconds <= 0 ? 0 : milliseconds > int.MaxValue ? int.MaxValue : (int)milliseconds;
        }
    }
}
