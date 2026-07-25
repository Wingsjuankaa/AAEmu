using System;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
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
        public void Aa8SocketInstallSkillObjectUsesNativeTypeTenLayout()
        {
            var skillObject = new SkillObjectSocketInstallOptions
            {
                Flag = SkillObjectType.SocketInstallOptions,
                AutoUseAaPoint = true,
                Count = 6,
                Continuous = true,
                InputDirection = 9
            };
            var stream = new PacketStream();

            skillObject.Write(stream);

            Assert.Equal(8, stream.Count);
            Assert.Equal((byte)SkillObjectType.SocketInstallOptions, stream[0]);
            Assert.Equal(1, stream[1]);
            Assert.Equal(6u, BitConverter.ToUInt32(stream.GetBytes(), 2));
            Assert.Equal(1, stream[6]);
            Assert.Equal(9, stream[7]);

            stream.Pos = 1;
            var decoded = Assert.IsType<SkillObjectSocketInstallOptions>(
                SkillObject.GetByType(SkillObjectType.SocketInstallOptions));
            decoded.Read(stream);
            decoded.ReadInputDirection(stream);

            Assert.True(decoded.AutoUseAaPoint);
            Assert.Equal(6u, decoded.Count);
            Assert.True(decoded.Continuous);
            Assert.Equal(9, decoded.InputDirection);
            Assert.Equal(stream.Count, stream.Pos);
        }

        [Fact]
        public void Aa8SocketChangeSkillObjectUsesNativeTypeElevenLayout()
        {
            var skillObject = new SkillObjectSocketChangeOptions
            {
                Flag = SkillObjectType.SocketChangeOptions,
                Index = 4,
                IsAll = true,
                InputDirection = 7
            };
            var stream = new PacketStream();

            skillObject.Write(stream);

            Assert.Equal(7, stream.Count);
            Assert.Equal((byte)SkillObjectType.SocketChangeOptions, stream[0]);
            Assert.Equal(4u, BitConverter.ToUInt32(stream.GetBytes(), 1));
            Assert.Equal(1, stream[5]);
            Assert.Equal(7, stream[6]);

            stream.Pos = 1;
            var decoded = Assert.IsType<SkillObjectSocketChangeOptions>(
                SkillObject.GetByType(SkillObjectType.SocketChangeOptions));
            decoded.Read(stream);
            decoded.ReadInputDirection(stream);

            Assert.Equal(4u, decoded.Index);
            Assert.True(decoded.IsAll);
            Assert.Equal(7, decoded.InputDirection);
            Assert.Equal(stream.Count, stream.Pos);
        }

        [Fact]
        public void Aa8EvolvingRerollSkillObjectUsesNativeTypeNineLayout()
        {
            var skillObject = new SkillObjectEvolvingRerollOptions
            {
                Flag = SkillObjectType.EvolvingRerollOptions,
                ModifierIndex = 3,
                ChangeToGroupId = 92870003,
                InputDirection = 5
            };
            var stream = new PacketStream();

            skillObject.Write(stream);

            Assert.Equal(10, stream.Count);
            Assert.Equal(
                (byte)SkillObjectType.EvolvingRerollOptions,
                stream[0]);
            Assert.Equal(3u, BitConverter.ToUInt32(stream.GetBytes(), 1));
            Assert.Equal(
                92870003u,
                BitConverter.ToUInt32(stream.GetBytes(), 5));
            Assert.Equal(5, stream[9]);

            stream.Pos = 1;
            var decoded = Assert.IsType<SkillObjectEvolvingRerollOptions>(
                SkillObject.GetByType(
                    SkillObjectType.EvolvingRerollOptions));
            decoded.Read(stream);
            decoded.ReadInputDirection(stream);

            Assert.Equal(3u, decoded.ModifierIndex);
            Assert.Equal(92870003u, decoded.ChangeToGroupId);
            Assert.Equal(5, decoded.InputDirection);
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

        [Fact]
        public void Aa8RejectedSkillWritesNativeResultByte()
        {
            var template = new SkillTemplate
            {
                Id = 37723
            };
            var packet = new SCSkillStartedPacket(
                template.Id,
                0,
                new SkillCasterUnit(1),
                new SkillCastUnitTarget(2),
                new Skill(template),
                new SkillObject())
            {
                RealCastTime = 0,
                BaseCastTime = 0
            };
            packet.SetSkillResult(SkillResult.CooldownTime);
            var stream = new PacketStream();

            packet.Write(stream);

            var trailer = stream.Count - 7;
            Assert.Equal((short)0, BitConverter.ToInt16(stream.GetBytes(), trailer));
            Assert.Equal((short)0, BitConverter.ToInt16(stream.GetBytes(), trailer + 2));
            Assert.Equal(0, stream[trailer + 4]);
            Assert.Equal((byte)SkillStartedExtraDataFlags.HasByte, stream[trailer + 5]);
            Assert.Equal((byte)SkillResult.CooldownTime, stream[trailer + 6]);
        }
    }
}
