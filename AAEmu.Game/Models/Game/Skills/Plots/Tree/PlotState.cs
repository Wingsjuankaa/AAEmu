using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using System;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.Game.Models.Game.Skills.Plots.Tree
{
    public class PlotState
    {
        private bool _cancellationRequest;
        private uint _castingEdgeId;
        private DateTime _castingStartedUtc;
        private int _castingDurationMs;
        private bool _castingUseable;
        private bool _castReleaseRequested;
        public Dictionary<uint, int> Tickets { get; set; }
        public int[] Variables { get; set; }
        public byte CombatDiceRoll { get; set; }
        public bool IsCasting { get; set; }
        public int CastingPercent { get; private set; }
        public int CurrentTargetCount { get; set; }
        public AoeDiminishingContext AoeDiminishingContext { get; }

        public Skill ActiveSkill { get; set; }
        public Unit Caster { get; set; }
        public SkillCaster CasterCaster { get; set; }
        public BaseUnit Target { get; set; }
        public SkillCastTarget TargetCaster { get; set; }
        public SkillObject SkillObject { get; set; }
        public List<(BaseUnit unit, uint buffId)> ChanneledBuffs { get; set; }

        public Dictionary<uint,List<GameObject>> HitObjects { get; set; }

        public PlotState(Unit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject, Skill skill)
        {
            _cancellationRequest = false;

            Caster = caster;
            CasterCaster = casterCaster;
            Target = target;
            TargetCaster = targetCaster;
            SkillObject = skillObject;
            ActiveSkill = skill;
            
            HitObjects = new Dictionary<uint, List<GameObject>>();
            Tickets = new Dictionary<uint, int>();
            ChanneledBuffs = new List<(BaseUnit, uint)>();
            Variables = new int[12];
            AoeDiminishingContext = new AoeDiminishingContext();
        }

        public bool CancellationRequested() => _cancellationRequest;

        public bool RequestCancellation()
        {
            if (ActiveSkill != null)
                ActiveSkill.Cancelled = true;
            return _cancellationRequest = true;
        }

        public void BeginCasting(PlotNextEvent edge, int durationMs, DateTime nowUtc)
        {
            if (edge == null || !edge.Casting)
                return;

            _castingEdgeId = edge.Id;
            _castingStartedUtc = nowUtc;
            _castingDurationMs = Math.Max(durationMs, 1);
            _castingUseable = edge.CastingUseable;
            _castReleaseRequested = false;
            CastingPercent = 0;
            IsCasting = true;
        }

        public bool TryReleaseCastingUseable(DateTime? nowUtc = null)
        {
            if (!IsCasting || !_castingUseable || _castingEdgeId == 0 ||
                _castReleaseRequested)
                return false;

            CastingPercent = CalculateCastingPercent(
                _castingStartedUtc,
                nowUtc ?? DateTime.UtcNow,
                _castingDurationMs);
            _castReleaseRequested = true;
            return true;
        }

        public bool ShouldRelease(PlotNextEvent edge) =>
            edge != null && _castReleaseRequested && edge.Id == _castingEdgeId;

        public void CompleteCasting(PlotNextEvent edge, bool released)
        {
            if (edge == null || !edge.Casting || edge.Id != _castingEdgeId)
                return;

            if (!released)
                CastingPercent = 100;
            IsCasting = false;
        }

        public static int CalculateCastingPercent(
            DateTime startedUtc,
            DateTime nowUtc,
            int durationMs)
        {
            if (durationMs <= 0)
                return 100;
            var elapsedMs = Math.Max(0, (nowUtc - startedUtc).TotalMilliseconds);
            return Math.Clamp((int)Math.Floor(elapsedMs * 100d / durationMs), 0, 100);
        }
    }
}
