using System;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using Xunit;

namespace AAEmu.Tests
{
    public class SkillStartedPacketSerializationTests
    {
        [Fact]
        public void Aa8TemperSkillObjectTypeSixUsesSupportItemLayout()
        {
            var skillObject = new SkillObjectItemGradeEnchantingSupport
            {
                Flag = SkillObjectType.ItemGradeEnchantingSupport,
                SupportItemId = 0x0102030405060708UL,
                AutoUseAaPoint = true,
                InputDirection = 9
            };
            var stream = new PacketStream();

            skillObject.Write(stream);

            Assert.Equal(11, stream.Count);
            Assert.Equal((byte)SkillObjectType.ItemGradeEnchantingSupport, stream[0]);
            Assert.Equal(
                skillObject.SupportItemId,
                BitConverter.ToUInt64(stream.GetBytes(), 1));
            Assert.Equal(1, stream[9]);
            Assert.Equal(9, stream[10]);
        }

        [Fact]
        public void Aa8SkillObjectTypeSixReadsSupportItemWithoutHistoricalString()
        {
            var stream = new PacketStream();
            stream.Write(0x0102030405060708UL);
            stream.Write(true);
            stream.Write((byte)9);
            stream.Pos = 0;
            var skillObject = Assert.IsType<SkillObjectItemGradeEnchantingSupport>(
                SkillObject.GetByType((SkillObjectType)6));

            skillObject.Read(stream);
            skillObject.ReadInputDirection(stream);

            Assert.Equal(0x0102030405060708UL, skillObject.SupportItemId);
            Assert.True(skillObject.AutoUseAaPoint);
            Assert.Equal(9, skillObject.InputDirection);
            Assert.Equal(stream.Count, stream.Pos);
        }

        [Fact]
        public void Aa8WritesRealAndNativeBaseCastTimesSeparately()
        {
            var template = new SkillTemplate
            {
                Id = 37723,
                CastingTime = 1500
            };
            var packet = new SCSkillStartedPacket(
                template.Id,
                7,
                new SkillCasterUnit(1),
                new SkillCastUnitTarget(2),
                new Skill(template),
                new SkillObject())
            {
                RealCastTime = 1345,
                BaseCastTime = template.CastingTime
            };
            var stream = new PacketStream();

            packet.Write(stream);

            var trailer = stream.Count - 6;
            Assert.Equal((short)134, BitConverter.ToInt16(stream.GetBytes(), trailer));
            Assert.Equal((short)150, BitConverter.ToInt16(stream.GetBytes(), trailer + 2));
            Assert.Equal(0, stream[trailer + 4]);
            Assert.Equal(0, stream[trailer + 5]);
        }
    }
}
