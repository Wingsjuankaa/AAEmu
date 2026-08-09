using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCBuffCreatedPacket : GamePacket
    {
        private readonly Buff _effect;

        public SCBuffCreatedPacket(Buff effect) : base(SCOffsets.SCBuffCreatedPacket, 5)
        {
            _effect = effect;
        }

        public override PacketStream Write(PacketStream stream)
        {
            var clientSkillId = GetClientSkillId(_effect);

            stream.Write(_effect.SkillCaster);             // skillCaster
            stream.Write((_effect.Caster is Character character) ? character.Id : 0); // casterId (type)
            stream.WriteBc(_effect.Owner.ObjId);           // targetId
            stream.Write(_effect.Index);                   // buffId (type)
            
            // всё, что ниже, относится к WriteData
            stream.Write(_effect.Template.BuffId);         // buffId
            stream.Write(_effect.Caster.Level);            // sourceLevel
            stream.Write(_effect.AbLevel);                 // sourceAbLevel
            // AA8's `s` field links a buff to the skill that owns a toggle.
            // It is not provenance for every skill-created buff. Sending the
            // origin skill here makes the client restart that skill's visual
            // cooldown when the buff is removed.
            stream.Write(clientSkillId);                   // toggle skillId
            stream.Write(_effect.Stack);                   // native buff_effects.stack
            _effect.WriteData(stream);
            /*
               sub_397ED240(v6);
               sub_397ED240(v2[3] / 0xAu);
               sub_397ED240(v2[4] / 0xAu);
               sub_397ED240(v2[5] / 0xAu);
             */
            return stream;
        }

        public override string Verbose()
        {
            return $" - buff={_effect.Template.BuffId}, index={_effect.Index}, originSkill={_effect.Skill?.Template.Id ?? 0}, toggleSkill={GetClientSkillId(_effect)}, caster={_effect.SkillCaster.Type}:{_effect.SkillCaster.ObjId}, owner={_effect.Owner.ObjId}, level={_effect.Caster.Level}, abilityLevel={_effect.AbLevel}, stack={_effect.Stack}";
        }

        private static uint GetClientSkillId(Buff effect)
        {
            var skillTemplate = effect?.Skill?.Template;
            return skillTemplate != null &&
                   skillTemplate.ToggleBuffId != 0 &&
                   skillTemplate.ToggleBuffId == effect.Template?.Id
                ? skillTemplate.Id
                : 0;
        }
    }
}
