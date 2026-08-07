using System;
using System.Numerics;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills.Buffs;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills
{
    public enum EffectState
    {
        Created,
        Acting,
        Finishing,
        Finished
    }

    public class Buff
    {
        private object _lock = new object();
        private int _count;

        public uint Index { get; set; }
        public Skill Skill { get; set; }
        // public EffectTemplate Template { get; set; }
        public BuffTemplate Template { get; set; }
        public Unit Caster { get; set; }
        public SkillCaster SkillCaster { get; set; }
        public BaseUnit Owner { get; set; }
        public EffectState State { get; set; }
        public bool InUse { get; set; }
        public int Duration { get; set; }
        public double Tick { get; set; }
        public DateTime StartTime { get; set; }
        public DateTime EndTime { get; set; }
        public int Charge { get; set; }
        public int Stack { get; set; } = 1;
        public bool Passive { get; set; }
        public ushort AbLevel { get; set; } // in 1.2 uint, in 3.0.3.0 ushort
        public BuffEvents Events { get; }
        public BuffTriggersHandler Triggers { get; }
        public Vector3? SavedPosition { get; }
        public uint SavedWorldId { get; }
        public uint SavedInstanceId { get; }

        public Buff(BaseUnit owner, Unit caster, SkillCaster skillCaster, BuffTemplate template, Skill skill, DateTime time)
        {
            Owner = owner;
            Caster = caster;
            SkillCaster = skillCaster;
            Template = template;
            Skill = skill;
            StartTime = time;
            EndTime = DateTime.MinValue;
            AbLevel = 1;
            Events = new BuffEvents();
            Triggers = new BuffTriggersHandler(this);
            if (template?.SavePosition == true && owner?.Transform != null)
            {
                if (ReferenceEquals(owner, caster) && skill?.CastOriginPosition != null)
                {
                    SavedPosition = skill.CastOriginPosition.Value;
                    SavedWorldId = skill.CastOriginWorldId;
                    SavedInstanceId = skill.CastOriginInstanceId;
                }
                else
                {
                    SavedPosition = owner.Transform.World.ClonePosition();
                    SavedWorldId = owner.Transform.WorldId;
                    SavedInstanceId = owner.Transform.InstanceId;
                }
            }
        }

        public void UpdateEffect()
        {
            Template.Start(Caster, Owner, this);
            if (Duration == 0)
                Duration = Template.GetDuration(AbLevel);
            if (StartTime == DateTime.MinValue)
            {
                StartTime = DateTime.UtcNow;
                EndTime = StartTime.AddMilliseconds(Duration);
            }

            Tick = Template.GetTick();

            if (Tick > 0)
            {
                var time = GetTimeLeft();
                if (time > 0)
                    _count = (int) (time / Tick + 0.5f + 1);
                else
                    _count = -1;
                EffectTaskManager.Instance.AddDispelTask(this, Tick);
            }
            else
                EffectTaskManager.Instance.AddDispelTask(this, GetTimeLeft());
        }

        public void ScheduleEffect(bool replace)
        {
            switch (State)
            {
                case EffectState.Created:
                {
                    State = EffectState.Acting;

                    Template.Start(Caster, Owner, this);

                    if (Duration == 0)
                        Duration = Template.GetDuration(AbLevel);
                    if (StartTime == DateTime.MinValue)
                    {
                        StartTime = DateTime.UtcNow;
                        EndTime = StartTime.AddMilliseconds(Duration);
                    }

                    Tick = Template.GetTick();

                    if (Tick > 0)
                    {
                        var time = GetTimeLeft();
                        if (time > 0)
                            _count = (int) (time / Tick + 0.5f + 1);
                        else
                            _count = -1;
                        EffectTaskManager.Instance.AddDispelTask(this, Tick);
                    }
                    else
                        EffectTaskManager.Instance.AddDispelTask(this, GetTimeLeft());

                    return;
                }
                case EffectState.Acting:
                {
                    // A StackRule.Extend reapplication moves the expiration
                    // deadline without replacing the active buff. The task
                    // scheduled for the former deadline must not expire it.
                    if (!Template.OnActionTime && GetTimeLeft() > 0)
                        return;

                    if (_count == -1)
                    {
                        if (Template.OnActionTime)
                        {
                            Template.TimeToTimeApply(Caster, Owner, this);
                            return;
                        }
                    }
                    else if (_count > 0)
                    {
                        _count--;
                        if (Template.OnActionTime && _count > 0)
                        {
                            Template.TimeToTimeApply(Caster, Owner, this);
                            return;
                        }
                    }

                    //Buff seems to come to natural expiration here
                    Events.OnTimeout(this, new OnTimeoutArgs());
                    State = EffectState.Finishing;
                    break;
                }
            }

            if (State == EffectState.Finishing)
            {
                State = EffectState.Finished;
                InUse = false;
                StopEffectTask(replace);
            }
        }

        public void Exit(bool replace = false)
        {
            if (State == EffectState.Finished)
                return;
            if (State != EffectState.Created)
            {
                State = EffectState.Finishing;
                ScheduleEffect(replace);
            }
            else
                State = EffectState.Finishing;
        }

        private void StopEffectTask(bool replace)
        {
            lock (_lock)
            {
                Triggers.UnsubscribeEvents();
                Owner.Buffs.RemoveEffect(this);
                Template.Dispel(Caster, Owner, this, replace);
            }
        }

        public void SetInUse(bool inUse, bool update)
        {
            InUse = inUse;
            if (update)
                UpdateEffect();
            else if (inUse)
                ScheduleEffect(false);
            else if (State != EffectState.Finished)
                State = EffectState.Finishing;
        }

        public bool IsEnded()
        {
            return State == EffectState.Finished || State == EffectState.Finishing;
        }

        public double GetTimeLeft()
        {
            if (Duration == 0)
                return -1;
            var time = (long) (StartTime.AddMilliseconds(Duration) - DateTime.UtcNow).TotalMilliseconds;
            return time > 0 ? time : 0;
        }

        public uint GetTimeElapsed()
        {
            var time = (uint) (DateTime.UtcNow - StartTime).TotalMilliseconds;
            return time > 0 ? time : 0;
        }

        public bool ExtendDuration(int extension, int maxLifeTime)
        {
            lock (_lock)
            {
                if (extension <= 0 || IsEnded())
                    return false;

                var currentRemaining = (int)Math.Ceiling(GetTimeLeft());
                var extendedRemaining = CalculateExtendedRemaining(
                    currentRemaining,
                    extension,
                    maxLifeTime);
                if (extendedRemaining <= currentRemaining)
                    return false;

                StartTime = DateTime.UtcNow;
                Duration = extendedRemaining;
                EndTime = StartTime.AddMilliseconds(Duration);
                return true;
            }
        }

        public static int CalculateExtendedRemaining(
            int currentRemaining,
            int extension,
            int maxLifeTime)
        {
            var remaining = Math.Max(0, currentRemaining);
            var added = Math.Max(0, extension);
            var extended = (long)remaining + added;

            if (maxLifeTime > 0)
                extended = Math.Min(extended, maxLifeTime);

            return extended > int.MaxValue ? int.MaxValue : (int)extended;
        }

        public void WriteData(PacketStream stream)
        {
            stream.WritePisc(Charge, Duration / 10, 0, (long)(Template.Tick / 10));
        }
        
        /// <summary>
        /// Consumes as much charge as possible. Remainder is returned
        /// </summary>
        /// <param name="value"></param>
        /// <returns></returns>
        public int ConsumeCharge(int value, Unit source = null)
        {
            if (value <= 0)
                return value;

            int remainder;
            int absorbed;
            bool exhausted;
            lock (_lock)
            {
                var previousCharge = Math.Max(0, Charge);
                absorbed = Math.Min(previousCharge, value);
                Charge = previousCharge - absorbed;
                remainder = value - absorbed;
                exhausted = previousCharge > 0 && Charge == 0;
            }

            if (exhausted)
            {
                Events.OnAbsorption(this, new OnAbsorptionArgs
                {
                    Source = source,
                    Target = Owner as Unit,
                    Amount = absorbed
                });
                Exit(false);
            }

            return remainder;
        }
    }
}
