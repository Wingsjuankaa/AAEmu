using System;
using System.Collections.Concurrent;
using System.Reflection;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.C2G;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using Microsoft.Data.Sqlite;
using Xunit;

namespace AAEmu.Tests
{
    public class Aa8HeirSorceryProtocolTests
    {
        private static string Runtime =>
            Environment.GetEnvironmentVariable("AAEMU8_SORCERY_RUNTIME") ??
            @"D:\Proyectos\AAemu\client_kakao\compact-8.0-runtime-transversal-sorcery-v10.sqlite3";

        [Fact]
        public void Aa8ClientRequestsUseNativeOpcodes()
        {
            Assert.Equal((ushort)0x08F, CSOffsets.CSActivateHeirSkillPacket);
            Assert.Equal((ushort)0x076, CSOffsets.CSResetHeirSkillPacket);
        }

        [Fact]
        public void Aa8HeirMutationRequestsAreRegisteredAtTheObservedEncryptionLevel()
        {
            var handlerField = typeof(GameNetwork).GetField(
                "_handler", BindingFlags.Instance | BindingFlags.NonPublic);
            var packetsField = typeof(GameProtocolHandler).GetField(
                "_packets", BindingFlags.Instance | BindingFlags.NonPublic);
            Assert.NotNull(handlerField);
            Assert.NotNull(packetsField);

            var handler = (GameProtocolHandler)handlerField.GetValue(GameNetwork.Instance);
            var packets = (ConcurrentDictionary<byte, ConcurrentDictionary<uint, Type>>)
                packetsField.GetValue(handler);

            Assert.Equal(
                typeof(CSActivateHeirSkillPacket),
                packets[5][CSOffsets.CSActivateHeirSkillPacket]);
            Assert.Equal(
                typeof(CSResetHeirSkillPacket),
                packets[5][CSOffsets.CSResetHeirSkillPacket]);
        }

        [Fact]
        public void ActiveTypeListUsesExactAa8Record()
        {
            var stream = new PacketStream();
            new SCListSkillActiveTypsPacket(new[]
            {
                new SkillActiveTypeEntry { HeirSkillType = 19, SkillType = 36474, ActiveType = 1 }
            }).Write(stream);

            Assert.Equal(new byte[]
            {
                1, 0, 0, 0,
                19, 0, 0, 0,
                0x7A, 0x8E, 0, 0,
                1
            }, stream.GetBytes());
        }

        [Fact]
        public void HeirListUsesExactAa8EighteenByteRecord()
        {
            var stream = new PacketStream();
            new SCHeirSkillListPacket(new[]
            {
                new HeirSkillListEntry
                {
                    HeirSkillId = 19,
                    BaseSkillId = 10752,
                    SuccessorSkillId = 36474,
                    SkillLevel = 6,
                    Ability = 6,
                    ActiveType = 1
                }
            }).Write(stream);

            Assert.Equal(new byte[]
            {
                1, 0, 0, 0,
                19, 0, 0, 0,
                0, 0x2A, 0, 0,
                0x7A, 0x8E, 0, 0,
                6, 0, 0, 0,
                6, 1
            }, stream.GetBytes());
        }

        [Fact]
        public void ActivationAndResetRepliesMatchNativeFieldOrder()
        {
            var activation = new PacketStream();
            new SCActivatedHeirSkillPacket(19, 36474, true).Write(activation);
            Assert.Equal(new byte[] { 19, 0, 0, 0, 0x7A, 0x8E, 0, 0, 1 }, activation.GetBytes());

            var reset = new PacketStream();
            new SCResetHeirSkillPacket(3, 36474, 6).Write(reset);
            Assert.Equal(new byte[] { 3, 0, 0, 0, 0x7A, 0x8E, 0, 0, 6 }, reset.GetBytes());
        }

        [Fact]
        public void ExactAa8RuntimeResolvesSorceryAncestralGraphAndSteps()
        {
            using (var connection = new SqliteConnection("Data Source=" + Runtime))
            {
                connection.Open();
                HeirGameData.Instance.Load(connection);
                HeirGameData.Instance.PostLoad();
            }

            Assert.Equal((byte)70, HeirGameData.Instance.MaxLevel);
            Assert.Equal((byte)1, HeirGameData.Instance.GetStepForLevel(1));
            Assert.Equal((byte)2, HeirGameData.Instance.GetStepForLevel(4));
            Assert.Equal((byte)12, HeirGameData.Instance.GetStepForLevel(70));
            Assert.Equal((byte)1, HeirGameData.Instance.GetFirstLevelForStep(1));
            Assert.Equal((byte)16, HeirGameData.Instance.GetFirstLevelForStep(6));

            Assert.True(HeirGameData.Instance.TryGetSelectableSuccessor(
                19, 36474, 1, out var flameBoltSuccessor));
            Assert.Equal(1, flameBoltSuccessor.Pos);
            Assert.True(HeirGameData.Instance.TryGetSelectableSuccessor(
                58, 43185, 6, out var meteorSuccessor));
            Assert.Equal(1, meteorSuccessor.Pos);
            Assert.False(HeirGameData.Instance.TryGetSelectableSuccessor(
                58, 43185, 5, out _));
        }

        [Fact]
        public void FreshAncestralOneCharacterReceivesEffectiveFlameboltActiveTypes()
        {
            using (var connection = new SqliteConnection("Data Source=" + Runtime))
            {
                connection.Open();
                HeirGameData.Instance.Load(connection);
                HeirGameData.Instance.PostLoad();
            }

            var character = new Character(null) { HierLevel = 1 };
            character.SkillActiveTypes = new CharacterSkillActiveTypes(character);

            var entries = character.SkillActiveTypes.BuildPacketEntries();

            Assert.Contains(entries, entry =>
                entry.HeirSkillType == 19 && entry.SkillType == 36474 && entry.ActiveType == 1);
            Assert.Contains(entries, entry =>
                entry.HeirSkillType == 19 && entry.SkillType == 36475 && entry.ActiveType == 1);
        }

        [Fact]
        public void VariantCastUsesOwnerAbilityLevelInsteadOfFallingBackToRankOne()
        {
            var factory = typeof(CSStartSkillPacket).GetMethod(
                "CreateVariantSkill", BindingFlags.NonPublic | BindingFlags.Static);
            Assert.NotNull(factory);
            var template = new SkillTemplate
            {
                Id = 36474,
                AbilityId = (byte)AbilityType.Magic,
                AbilityLevel = 25,
                LevelStep = 5
            };

            var skill = (Skill)factory.Invoke(null, new object[] { template, new LevelFiftyFiveUnit() });

            Assert.Equal((byte)7, skill.Level);
        }

        [Theory]
        [InlineData(false, 0u, 36474u, false, true)]
        [InlineData(false, 0u, 36474u, true, false)]
        [InlineData(true, 36474u, 36475u, true, true)]
        [InlineData(true, 36474u, 36475u, false, false)]
        [InlineData(true, 36474u, 36474u, true, false)]
        public void NativeChangeFlagMustMatchTheCurrentSelectionState(
            bool hasCurrent, uint current, uint requested, bool isChange, bool expected)
        {
            var validator = typeof(CharacterHeirSkills).GetMethod(
                "IsValidActivationTransition", BindingFlags.NonPublic | BindingFlags.Static);
            Assert.NotNull(validator);

            var actual = (bool)validator.Invoke(
                null, new object[] { hasCurrent, current, requested, isChange });

            Assert.Equal(expected, actual);
        }

        private sealed class LevelFiftyFiveUnit : Unit
        {
            public override int GetAbLevel(AbilityType type) { return 55; }
        }
    }
}
