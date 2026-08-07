using AAEmu.Commons.Network;

using System.Collections.Generic;
using AAEmu.Game.Models.Game.Skills.Effects;

namespace AAEmu.Game.Models.Game.Skills
{
    public enum CastType : byte
    {
        Skill = 0,
        Plot = 1,
        Buff = 2,
        BuffTarget = 3,
        DestroyTarget = 4
    }

    public abstract class CastAction : PacketMarshaler
    {
        public CastType Type { get; set; }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((byte) Type);
            return stream;
        }
    }

    public class CastSkill : CastAction
    {
        private uint _skillId;
        private ushort _tlId;
        
        public uint SkillId { get => _skillId; }
        public ushort TlId { get => _tlId; }
        
        public CastSkill(uint skillId, ushort tlId)
        {
            Type = CastType.Skill;
            _skillId = skillId;
            _tlId = tlId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(_skillId);
            stream.Write(_tlId);
            return stream;
        }
    }

    public class CastPlot : CastAction
    {
        private uint _plotId;
        private ushort _tlId;
        private uint _eventId;
        private uint _skillId;
        private readonly bool _aoeDiminishing;
        private readonly AoeDiminishingContext _aoeDiminishingContext;

        public CastPlot(uint plotId, ushort tlId, uint eventId, uint skillId,
            bool aoeDiminishing = false,
            AoeDiminishingContext aoeDiminishingContext = null)
        {
            Type = CastType.Plot;
            _plotId = plotId;
            _tlId = tlId;
            _eventId = eventId;
            _skillId = skillId;
            _aoeDiminishing = aoeDiminishing;
            _aoeDiminishingContext = aoeDiminishingContext;
        }

        public float GetAoeDiminishingMultiplier(uint targetId)
        {
            return _aoeDiminishing && _aoeDiminishingContext != null
                ? _aoeDiminishingContext.GetOrAssignMultiplier(targetId)
                : 1f;
        }

        public void ResetAoeDiminishing()
        {
            _aoeDiminishingContext?.Reset();
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(_plotId); // type(id)
            stream.Write(_tlId);
            stream.Write(_eventId); // type(id)
            stream.Write(_skillId); // type(id)
            return stream;
        }
    }

    public sealed class AoeDiminishingContext
    {
        private readonly Dictionary<uint, float> _targetMultipliers =
            new Dictionary<uint, float>();

        public float GetOrAssignMultiplier(uint targetId)
        {
            if (_targetMultipliers.TryGetValue(targetId, out var multiplier))
                return multiplier;

            multiplier = DamageEffectCalculator.CalculateAoeDiminishingMultiplier(
                _targetMultipliers.Count);
            _targetMultipliers[targetId] = multiplier;
            return multiplier;
        }

        public void Reset()
        {
            _targetMultipliers.Clear();
        }
    }

    public class CastBuff : CastAction
    {
        private Buff _buff;

        public Buff Buff => _buff;

        public CastBuff(Buff buff)
        {
            Type = CastType.Buff;
            _buff = buff;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(_buff.Template.BuffId);
            stream.WriteBc(_buff.Owner.ObjId);
            stream.Write(_buff.Index);
            stream.Write(true); // t
            stream.Write(false); // t
            return stream;
        }
    }

    public class CastUnk2 : CastAction
    {
        public CastUnk2()
        {
            Type = CastType.BuffTarget;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(0); // type(id), pt
            stream.Write(0); // buffId
            stream.WriteBc(0);
            return stream;
        }
    }

    public class CastUnk3 : CastAction
    {
        public CastUnk3()
        {
            Type = CastType.DestroyTarget;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write(0); // type(id), dt
            stream.WriteBc(0);
            return stream;
        }
    }
}
