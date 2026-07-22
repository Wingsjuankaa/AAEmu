using System;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.SkillControllers;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Templates
{
    public class SkillControllerTemplate : EffectTemplate
    {
        public uint KindId { get; set; }
        public int[] Value { get; set; }
        public byte ActiveWeaponId { get; set; }
        // TODO 1.2 // public uint EndSkillId { get; set; }
        public override bool OnActionTime { get; }

        public SkillControllerTemplate()
        {
            Value = new int[15];
        }

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj,
            EffectSource source, SkillObject skillObject, DateTime time, CompressedGamePackets packetBuilder = null)
        {
            _log.Debug("SkillControllerTemplate.Apply: sc_id={0}, kind={1}, caster={2}, target={3}",
                Id, KindId, caster?.ObjId, target?.ObjId);

            var owner = caster as Unit;
            var targetUnit = target as Unit;
            if (owner == null || targetUnit == null)
            {
                _log.Warn("Cannot apply skill controller {0}: owner or target is not a Unit", Id);
                return;
            }

            var controller = SkillController.CreateSkillController(this, owner, targetUnit);
            if (controller == null)
            {
                _log.Warn("Skill controller {0} kind {1} is not implemented", Id, KindId);
                return;
            }

            owner.ActiveSkillController?.End();
            owner.ActiveSkillController = controller;
            controller.Execute();
        }
    }
}
