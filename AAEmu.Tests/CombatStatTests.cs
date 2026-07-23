using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class CombatStatTests
    {
        [Fact]
        public void BattleFocusRankTwoAppliesAndRemovesNativePercentagePointBonuses()
        {
            var unit = new TestUnit
            {
                NaturalMeleeParry = 7.8f,
                NaturalMeleeCriticalBonus = 50f
            };
            var template = new BuffTemplate { Id = 7651 };
            template.Bonuses.Add(new BonusTemplate
            {
                Attribute = UnitAttribute.MeleeParryMul,
                ModifierType = UnitModifierType.Value,
                Value = 300
            });
            template.Bonuses.Add(new BonusTemplate
            {
                Attribute = UnitAttribute.MeleeCriticalBonus,
                ModifierType = UnitModifierType.Value,
                Value = 200
            });
            var buff = new Buff(
                unit,
                unit,
                new SkillCasterUnit(unit.ObjId),
                template,
                null,
                DateTime.UtcNow)
            {
                Index = 7651,
                AbLevel = 31,
                Passive = true
            };

            template.Start(unit, unit, buff);

            Assert.Equal(37.8f, unit.MeleeParryRate, 3);
            Assert.Equal(70f, unit.MeleeCriticalBonus, 3);
            Assert.Equal(
                30f,
                CombatStatOverrideManager.Instance.GetDirectNativeBonus(
                    unit,
                    CombatStatKind.MeleeParry),
                3);

            template.Dispel(unit, unit, buff);

            Assert.Equal(7.8f, unit.MeleeParryRate, 3);
            Assert.Equal(50f, unit.MeleeCriticalBonus, 3);
        }

        [Fact]
        public void DynamicNativeModifierIsNotMisinterpretedAsFixedValue()
        {
            var unit = new TestUnit();
            var template = new BuffTemplate { Id = 22278 };
            template.Bonuses.Add(new BonusTemplate
            {
                Attribute = UnitAttribute.MaxCombatResource,
                ModifierType = UnitModifierType.Value,
                Value = 1,
                DynamicValue = 1
            });
            var buff = new Buff(
                unit,
                unit,
                new SkillCasterUnit(unit.ObjId),
                template,
                null,
                DateTime.UtcNow)
            {
                Index = 22278,
                Passive = true
            };

            template.Start(unit, unit, buff);

            Assert.Equal(0d, unit.Calculate(0d, UnitAttribute.MaxCombatResource));
        }

        [Fact]
        public void CombatStatOverrideIsTemporaryAndDoesNotChangeBaseValue()
        {
            var unit = new TestUnit
            {
                ObjId = 900001,
                MeleeParryRate = 7.8f
            };
            var service = CombatStatOverrideManager.Instance;
            service.ClearAll(unit);

            service.Set(unit, CombatStatKind.MeleeParry, 100f);

            Assert.Equal(7.8f, service.GetBaseValue(unit, CombatStatKind.MeleeParry), 3);
            Assert.Equal(100f, service.Resolve(unit, CombatStatKind.MeleeParry, unit.MeleeParryRate), 3);
            Assert.True(service.TryGet(unit, CombatStatKind.MeleeParry, out var value));
            Assert.Equal(100f, value);

            service.ClearAll(unit);

            Assert.False(service.TryGet(unit, CombatStatKind.MeleeParry, out _));
            Assert.Equal(7.8f, service.Resolve(unit, CombatStatKind.MeleeParry, unit.MeleeParryRate), 3);
        }

        [Theory]
        [InlineData(0f)]
        [InlineData(101f)]
        public void CombatStatOverrideRejectsOutOfRangeValues(float value)
        {
            var unit = new TestUnit { ObjId = 900002 };
            var service = CombatStatOverrideManager.Instance;
            service.ClearAll(unit);

            Assert.Throws<ArgumentOutOfRangeException>(
                () => service.Set(unit, CombatStatKind.MeleeParry, value));
        }

        [Fact]
        public void NativeModifierRetainsInt64AndSaturatesOnlyAtLegacyRuntimeBoundary()
        {
            var template = new BonusTemplate { Value = 9999999999989752L };

            Assert.Equal(9999999999989752L, template.Value);
            Assert.Equal(int.MaxValue, Bonus.ToRuntimeValue(template.Value));
        }

        [Fact]
        public void BuffCreatedPacketSerializesNativeBuffEffectStack()
        {
            var unit = new TestUnit { ObjId = 77, Level = 55 };
            var buff = new Buff(
                unit,
                unit,
                new SkillCasterUnit(unit.ObjId),
                new BuffTemplate { Id = 7651 },
                null,
                DateTime.UtcNow)
            {
                Index = 7,
                AbLevel = 31,
                Stack = 9,
                Duration = 20000
            };
            var output = new PacketStream();

            new SCBuffCreatedPacket(buff).Write(output);

            var input = new PacketStream(output.GetBytes());
            Assert.Equal((byte)SkillCasterType.Unit, input.ReadByte());
            Assert.Equal(unit.ObjId, input.ReadBc());
            Assert.Equal(0u, input.ReadUInt32());
            Assert.Equal(unit.ObjId, input.ReadBc());
            Assert.Equal(buff.Index, input.ReadUInt32());
            Assert.Equal(buff.Template.Id, input.ReadUInt32());
            Assert.Equal(unit.Level, input.ReadByte());
            Assert.Equal(buff.AbLevel, input.ReadUInt16());
            Assert.Equal(0u, input.ReadUInt32());
            Assert.Equal(buff.Stack, input.ReadInt32());
        }

        private class TestUnit : Unit
        {
            public float NaturalMeleeParry { get; set; }
            public float NaturalMeleeCriticalBonus { get; set; }

            public override float MeleeParryRate
            {
                get => NaturalMeleeParry
                    + (float)(CalculateWithBonuses(0d, UnitAttribute.MeleeParryMul) / 10d);
                set => NaturalMeleeParry = value;
            }

            public override float MeleeCriticalBonus
            {
                get => NaturalMeleeCriticalBonus
                    + (float)(CalculateWithBonuses(0d, UnitAttribute.MeleeCriticalBonus) / 10d);
                set => NaturalMeleeCriticalBonus = value;
            }

            public double Calculate(double value, UnitAttribute attribute)
            {
                return CalculateWithBonuses(value, attribute);
            }
        }
    }
}
