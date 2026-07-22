    using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCUnitDamagedPacket : GamePacket
    {
        private readonly CastAction _castAction;
        private readonly SkillCaster _skillCaster;
        private readonly uint _casterId;
        private readonly uint _targetId;
        private readonly int _damage;
        private readonly byte _crimeState;
        private readonly int _absorbed;
        public int _manaBurn;
        
        public byte HoldableId { get; set; }
        public int ElementDamage { get; set; }
        public bool ShowElementEffect { get; set; }
        public uint ElementType { get; set; }
        public SkillHitType HitType { get; set; }

        public SCUnitDamagedPacket(CastAction castAction, SkillCaster skillCaster, uint casterId, uint targetId, int damage, int absorbed)
            : base(SCOffsets.SCUnitDamagedPacket, 5)
        {
            _castAction = castAction;
            _skillCaster = skillCaster;
            _casterId = casterId;
            _targetId = targetId;
            _damage = damage;
            _absorbed = absorbed;
        }

        public SCUnitDamagedPacket(CastAction castAction, SkillCaster skillCaster, uint casterId, uint targetId, int damage)
            : base(SCOffsets.SCUnitDamagedPacket, 5)
        {
            _castAction = castAction;
            _skillCaster = skillCaster;
            _casterId = casterId;
            _targetId = targetId;
            _damage = damage;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_castAction);
            stream.Write(_skillCaster);
            stream.WriteBc(_casterId);
            stream.WriteBc(_targetId);
            stream.Write(_crimeState);
            stream.WritePisc(_damage, _absorbed);
            stream.WritePisc(0, 0, _manaBurn);
            stream.Write(HoldableId);
            stream.Write(ElementDamage);
            stream.Write(ShowElementEffect);
            stream.Write(ElementType);
            stream.Write((ushort)(288 | (ushort)HitType));
            stream.Write((byte)1); // Damage flags; debug payload is disabled.
            stream.Write((byte)1); // Damage result.
            return stream;
        }

        public override string Verbose()
        {
            var cast = _castAction switch
            {
                CastSkill skill => $"skill:{skill.SkillId}/tl:{skill.TlId}",
                _ => _castAction.Type.ToString()
            };

            return $" - cast={cast}, caster={_skillCaster.Type}:{_skillCaster.ObjId}/{_casterId}, target={_targetId}, damage={_damage}, absorbed={_absorbed}, manaBurn={_manaBurn}, elementDamage={ElementDamage}, showElement={ShowElementEffect}, elementType={ElementType}, hit={HitType}";
        }
    }
}
