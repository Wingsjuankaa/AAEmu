using System;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class BubbleEffect : EffectTemplate
    {
        public uint KindId { get; set; }

        public override bool OnActionTime => false;

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj,
            EffectSource source, SkillObject skillObject, DateTime time, CompressedGamePackets packetBuilder = null)
        {
            if (target == null)
                return;

            _log.Trace("BubbleEffect, Id {0}, KindId {1}, ObjId {2}", Id, KindId, target.ObjId);
            target.BroadcastPacket(
                new SCChatBubblePacket(target.ObjId, (byte)KindId, 2, Id, string.Empty), true);
        }
    }
}
