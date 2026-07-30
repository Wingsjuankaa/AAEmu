using System;
using System.Collections;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

using Xunit;

namespace AAEmu.Tests
{
    public class NativeQuestProtocolTests
    {
        [Fact]
        public void EmptyWorldContentFilterInitializesAllNativeQuestIndexes()
        {
            var packet = new SCFilterPacket();

            Assert.Equal(0x138, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                new byte[] { 0, 0, 0, 0 },
                packet.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void WorldContentFilterUsesUInt32SizeFollowedByRawBytes()
        {
            var packet = new SCFilterPacket(new byte[] { 0x11, 0x22, 0x33 });

            Assert.Equal(
                new byte[] { 3, 0, 0, 0, 0x11, 0x22, 0x33 },
                packet.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void DoodadQuestCompletionUsesNativeAa8BcThenQuestIdLayout()
        {
            var packet = new SCDoodadCompleteQuestPacket(0x1234, 2532);
            var expected = new PacketStream();
            expected.WriteBc(0x1234);
            expected.Write(2532u);

            Assert.Equal(0x0AD, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                expected.GetBytes().ToArray(),
                packet.Write(new PacketStream()).GetBytes().ToArray());
        }

        [Fact]
        public void EmptyActiveQuestSnapshotUsesAa8OpcodeAndInt32Count()
        {
            var packet = new SCQuestsPacket(Array.Empty<Quest>());

            Assert.Equal(0x1B4, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(new byte[] { 0, 0, 0, 0 }, packet.Write(new PacketStream()).GetBytes());
        }

        [Fact]
        public void ActiveQuestUsesAa8VariableWidthObjectiveEncoding()
        {
            var quest = new Quest
            {
                Id = 1,
                TemplateId = 330,
                Status = QuestStatus.Ready,
                Objectives = new[]
                {
                    0,
                    255,
                    256,
                    65535,
                    65536,
                    0xFFFFFF,
                    0x1000000,
                    -1,
                    1,
                    int.MinValue
                }
            };

            var bytes = quest.Write(new PacketStream()).GetBytes();
            var objectiveBytes = bytes.Skip(sizeof(long) + sizeof(uint) + sizeof(byte))
                .Take(28)
                .ToArray();

            Assert.Equal(
                new byte[]
                {
                    0x50,
                    0x00,
                    0xFF,
                    0x00, 0x01,
                    0xFF, 0xFF,
                    0xFA,
                    0x00, 0x00, 0x01,
                    0xFF, 0xFF, 0xFF,
                    0x00, 0x00, 0x00, 0x01,
                    0xFF, 0xFF, 0xFF, 0xFF,
                    0x0C,
                    0x01,
                    0x00, 0x00, 0x00, 0x80
                },
                objectiveBytes);
        }

        [Fact]
        public void EmptyAa8ObjectiveSetUsesThreeWidthHeadersAndTenPayloadBytes()
        {
            var quest = new Quest
            {
                Id = 1,
                TemplateId = 330,
                Status = QuestStatus.Ready
            };

            var bytes = quest.Write(new PacketStream()).GetBytes();
            var objectiveBytes = bytes.Skip(sizeof(long) + sizeof(uint) + sizeof(byte))
                .Take(13)
                .ToArray();

            Assert.Equal(new byte[13], objectiveBytes);
        }

        [Fact]
        public void QuestContextUpdateUsesTenAa8VariableWidthComponentValues()
        {
            var quest = new Quest
            {
                Id = 1,
                TemplateId = 330,
                Status = QuestStatus.Ready
            };
            var questLength = quest.Write(new PacketStream()).Count;
            var packet = new SCQuestContextUpdatedPacket(quest, 1521);

            var componentBytes = packet.Write(new PacketStream()).GetBytes()
                .Skip(questLength)
                .ToArray();

            Assert.Equal(
                new byte[]
                {
                    0x01,
                    0xF1, 0x05,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00,
                    0x00
                },
                componentBytes);
        }

        [Fact]
        public void CompletedQuestSnapshotWritesInt32CountIndexAndEightByteBody()
        {
            var completed = new CompletedQuest(5)
            {
                Body = new BitArray(new byte[]
                {
                    0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80
                })
            };
            var packet = new SCCompletedQuestsPacket(new[] { completed });

            Assert.Equal(0x081, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                new byte[]
                {
                    0x01, 0x00, 0x00, 0x00,
                    0x05, 0x00, 0x00, 0x00,
                    0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80
                },
                packet.Write(new PacketStream()).GetBytes().ToArray());
        }

        [Fact]
        public void SystemFactionSnapshotUsesAa8FieldsForQuestRequirementEvaluation()
        {
            var faction = new SystemFaction
            {
                Id = 101,
                MotherId = 148,
                Name = "Crescent Throne",
                OwnerId = 1,
                OwnerName = "",
                UnitOwnerType = 1,
                PoliticalSystem = 1,
                Created = DateTime.MinValue,
                AggroLink = false,
                DiplomacyTarget = false,
                AllowChangeName = 0,
                IntegrationFaction = true
            };
            var packet = new SCSystemFactionListPacket(faction);
            var expected = new PacketStream();
            expected.Write((byte) 1);
            expected.Write(101u);
            expected.Write(148u);
            expected.Write("Crescent Throne");
            expected.Write(1u);
            expected.Write("");
            expected.Write((sbyte) 1);
            expected.Write((byte) 1);
            expected.Write(DateTime.MinValue);
            expected.Write(false);
            expected.Write(false);
            expected.Write((byte) 0);
            expected.Write(DateTime.MinValue);
            expected.Write(true);

            Assert.Equal(0x101, packet.TypeId);
            Assert.Equal(5, packet.Level);
            Assert.Equal(
                expected.GetBytes().ToArray(),
                packet.Write(new PacketStream()).GetBytes().ToArray());
        }

        [Fact]
        public void NativeFactionHierarchyResolutionSupportsQuestRequirementKind56()
        {
            var factions = new[]
            {
                new SystemFaction { Id = 101, MotherId = 148 },
                new SystemFaction { Id = 148, MotherId = 0 }
            }.ToDictionary(faction => faction.Id);

            var chain = FactionManager.ResolveMotherChain(
                101,
                id => factions.TryGetValue(id, out var faction) ? faction : null);

            Assert.Equal(new uint[] { 101, 148 }, chain);
            Assert.Contains(148u, chain);
        }

        [Fact]
        public void FactionHierarchyResolutionStopsOnCycles()
        {
            var factions = new[]
            {
                new SystemFaction { Id = 101, MotherId = 148 },
                new SystemFaction { Id = 148, MotherId = 101 }
            }.ToDictionary(faction => faction.Id);

            var chain = FactionManager.ResolveMotherChain(
                101,
                id => factions.TryGetValue(id, out var faction) ? faction : null);

            Assert.Equal(new uint[] { 101, 148 }, chain);
        }

        [Fact]
        public void ImmediateReadyQuestAdvancesPastMissingProgressStep()
        {
            var template = new QuestTemplate { Id = 330 };
            template.Components.Add(
                1520,
                new QuestComponent
                {
                    Id = 1520,
                    KindId = QuestComponentKind.Start
                });
            template.Components.Add(
                1521,
                new QuestComponent
                {
                    Id = 1521,
                    KindId = QuestComponentKind.Ready
                });
            var quest = new Quest(template)
            {
                Status = QuestStatus.Ready,
                Step = QuestComponentKind.Progress,
                ComponentId = 1520
            };

            var changed = quest.NormalizeImmediateReadyStep();

            Assert.True(changed);
            Assert.Equal(QuestComponentKind.Ready, quest.Step);
            Assert.Equal(1521u, quest.ComponentId);
        }

        [Fact]
        public void ReadyQuestWithProgressComponentIsNotRewritten()
        {
            var template = new QuestTemplate { Id = 331 };
            template.Components.Add(
                1600,
                new QuestComponent
                {
                    Id = 1600,
                    KindId = QuestComponentKind.Progress
                });
            template.Components.Add(
                1601,
                new QuestComponent
                {
                    Id = 1601,
                    KindId = QuestComponentKind.Ready
                });
            var quest = new Quest(template)
            {
                Status = QuestStatus.Ready,
                Step = QuestComponentKind.Progress,
                ComponentId = 1600
            };

            var changed = quest.NormalizeImmediateReadyStep();

            Assert.False(changed);
            Assert.Equal(QuestComponentKind.Progress, quest.Step);
            Assert.Equal(1600u, quest.ComponentId);
        }
    }
}
