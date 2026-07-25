using System;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;

namespace AAEmu.Game.Core.Packets.G2C
{
    [Flags]
    public enum SkillStartedExtraDataFlags : byte
    {
        None = 0,
        HasByte = 1,
        HasUShort = 2,
        HasUInt = 4
    }

    public class SCSkillStartedPacket : GamePacket
    {
        private readonly uint _id;
        private readonly ushort _tl;
        private readonly SkillCaster _caster;
        private readonly SkillCastTarget _target;
        private readonly Skill _skill;
        private readonly SkillObject _skillObject;
        private SkillStartedExtraDataFlags _extraDataFlags;
        private byte _extraDataByte;
        private ushort _extraDataUShort;
        private uint _extraDataUInt;
        public int RealCastTime { get; set; }
        public int BaseCastTime { get; set; }

        public SCSkillStartedPacket(uint id, ushort tl, SkillCaster caster, SkillCastTarget target, Skill skill, SkillObject skillObject) 
            : base(SCOffsets.SCSkillStartedPacket, 5)
        {
            _id = id;
            _tl = tl;
            _caster = caster;
            _target = target;
            _skill = skill;
            _skillObject = skillObject;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_id);
            stream.Write(_tl);
            stream.Write(_caster);
            stream.Write(_target);
            stream.Write(_skillObject);
            stream.Write((short)(RealCastTime / 10));
            stream.Write((short)(BaseCastTime / 10));
            stream.Write(false); // castSynergy // (short)0
            stream.Write((byte)_extraDataFlags);
            if (_extraDataFlags.HasFlag(SkillStartedExtraDataFlags.HasByte))
                stream.Write(_extraDataByte);
            if (_extraDataFlags.HasFlag(SkillStartedExtraDataFlags.HasUShort))
                stream.Write(_extraDataUShort);
            if (_extraDataFlags.HasFlag(SkillStartedExtraDataFlags.HasUInt))
                stream.Write(_extraDataUInt);
            
            return stream;
        }

        public SCSkillStartedPacket SetSkillResult(SkillResult skillResult)
        {
            if (skillResult == SkillResult.Success)
                _extraDataFlags &= ~SkillStartedExtraDataFlags.HasByte;
            else
                _extraDataFlags |= SkillStartedExtraDataFlags.HasByte;
            _extraDataByte = (byte)skillResult;
            return this;
        }

        public SCSkillStartedPacket SetResultUShort(ushort value)
        {
            if (value == 0)
                _extraDataFlags &= ~SkillStartedExtraDataFlags.HasUShort;
            else
                _extraDataFlags |= SkillStartedExtraDataFlags.HasUShort;
            _extraDataUShort = value;
            return this;
        }

        public SCSkillStartedPacket SetResultUInt(uint value)
        {
            if (value == 0)
                _extraDataFlags &= ~SkillStartedExtraDataFlags.HasUInt;
            else
                _extraDataFlags |= SkillStartedExtraDataFlags.HasUInt;
            _extraDataUInt = value;
            return this;
        }

        public override string Verbose()
        {
            var itemSource = _caster is SkillItem item
                ? $", item={item.ItemId}/{item.ItemTemplateId}, itemType1={item.Type1}, itemType2={item.Type2}"
                : string.Empty;
            var itemTarget = _target is SkillCastItemTarget targetItem
                ? $", targetItem={targetItem.Id}, targetType1={targetItem.Type1}, targetType2={targetItem.Type2}"
                : string.Empty;
            var support = _skillObject is SkillObjectItemGradeEnchantingSupport supportObject
                ? $", supportItem={supportObject.SupportItemId}, autoUseAaPoint={supportObject.AutoUseAaPoint}"
                : string.Empty;
            var evolvingMaterials =
                _skillObject is SkillObjectEvolvingMaterials materialsObject
                    ? $", materialItems={DescribeMaterialItems(materialsObject)}, autoUseAaPoint={materialsObject.AutoUseAaPoint}"
                    : string.Empty;
            return
                $" - skill={_id}, tl={_tl}, caster={_caster.Type}:{_caster.ObjId}{itemSource}, " +
                $"target={_target.Type}:{_target.ObjId}{itemTarget}, skillObject={_skillObject.Flag}, " +
                $"inputDirection={_skillObject.InputDirection}{support}{evolvingMaterials}, realCast={RealCastTime}, " +
                $"baseCast={BaseCastTime}, startAnim={_skill.Template.StartAnimId}, " +
                $"result={(_extraDataFlags.HasFlag(SkillStartedExtraDataFlags.HasByte) ? _extraDataByte : 0)}";
        }

        private static string DescribeMaterialItems(
            SkillObjectEvolvingMaterials materialsObject)
        {
            return materialsObject.TryGetMaterialItemIds(out var materialIds)
                ? string.Join(",", materialIds)
                : $"invalid:{BitConverter.ToString(materialsObject.EncodedMaterialItemIds)}";
        }
    }
}
