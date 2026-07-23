using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCSkillFiredPacket : GamePacket
    {
        private uint _id;
        private ushort _tl;
        private SkillCaster _caster;
        private SkillCastTarget _target;
        private SkillObject _skillObject;
        private Skill _skill;
        private short _effectDelay = 37;
        private uint _fireAnimId;
        private bool _dist;

        public short ComputedDelay { get; set; }

        public SCSkillFiredPacket(uint id, ushort tl, SkillCaster caster, SkillCastTarget target, Skill skill, SkillObject skillObject) 
            : base(SCOffsets.SCSkillFiredPacket, 5)
        {
            _id = id;
            _tl = tl;
            _caster = caster;
            _target = target;
            _skill = skill;
            _skillObject = skillObject;
            _fireAnimId = skill.Template.FireAnimId;
        }

        public SCSkillFiredPacket(uint id, ushort tl, SkillCaster caster, SkillCastTarget target, Skill skill,
            SkillObject skillObject, uint fireAnimId)
            : this(id, tl, caster, target, skill, skillObject)
        {
            _fireAnimId = fireAnimId;
        }

        public SCSkillFiredPacket(uint id, ushort tl, SkillCaster caster, SkillCastTarget target, Skill skill, SkillObject skillObject, short effectDelay = 37, int fireAnimId = 2, bool dist = true)
            : base(SCOffsets.SCSkillFiredPacket, 5)
        {
            _id = id;
            _tl = tl;
            _caster = caster;
            _target = target;
            _skill = skill;
            _skillObject = skillObject;
            _effectDelay = effectDelay;
            _fireAnimId = (uint)fireAnimId;
            _dist = dist;
        }


        public override PacketStream Write(PacketStream stream)
        {
            // Kakao 8.0 r558734 serializes the skill type and fire animation
            // together as PISC near the end of the packet. Writing the skill
            // type here shifts every following field and makes the client
            // discard the visual transition while the server still applies it.
            stream.Write(_tl);       // sid - skill transaction id
            stream.Write(_caster);
            stream.Write(_target);
            stream.Write(_skillObject);
            stream.Write((short)(ComputedDelay / 10 + 10));
            stream.Write((short)(_skill.Template.ChannelingTime / 10 + 10)); // TODO +10 It became visible flying arrows
            stream.Write((byte)0); // f - When changed to 1 when firing an auto-casting skill, will make the little blue arrow.
            stream.WritePisc(_id, _fireAnimId);
            stream.Write((byte)0); // flag

            return stream;
        }

        public override string Verbose()
        {
            return $" - skill={_id}, tl={_tl}, caster={_caster.Type}:{_caster.ObjId}, target={_target.Type}:{_target.ObjId}, fireAnim={_fireAnimId}, computedDelay={ComputedDelay}, channeling={_skill.Template.ChannelingTime}";
        }
    }
}
