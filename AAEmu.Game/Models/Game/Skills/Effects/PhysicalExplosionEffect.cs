using System;
using System.Numerics;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects
{
    public class PhysicalExplosionEffect : EffectTemplate
    {
        public float Radius { get; set; }
        public float HoleSize { get; set; }
        public float Pressure { get; set; }

        public override bool OnActionTime => false;

        public override void Apply(Unit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
            CastAction castObj, EffectSource source, SkillObject skillObject, DateTime time,
            CompressedGamePackets packetBuilder = null)
        {
            if (target == null)
                return;

            var distance = caster == null
                ? 0f
                : Vector3.Distance(caster.Transform.World.Position, target.Transform.World.Position);
            var effectivePressure = ForcedMovementEffectCalculator.CalculateExplosionPressure(
                distance, Radius, Pressure);

            // The dedicated server forwards this descriptor to CryEngine as a
            // pe_explosion. Damage is a separate plot effect. AAEmu has no
            // physical-world geometry/mass solver, so keeping it declarative is
            // more accurate than inventing unit damage or a linear knockback.
            _log.Trace(
                "AA8 PhysicalExplosion radius={0:F3} holeSize={1:F3} pressure={2:F3} effectivePressure={3:F3}",
                Radius, HoleSize, Pressure, effectivePressure);
        }
    }
}
