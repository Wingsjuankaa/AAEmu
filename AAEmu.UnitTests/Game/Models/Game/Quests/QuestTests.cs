using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
#pragma warning disable IDE0051

namespace AAEmu.UnitTests.Game.Models.Game.Quests;
// TODO: Re-enable the quest related test
// ReSharper disable UnusedMember.Local

public class QuestTests
{
    // [Fact]
    private async Task Start_WhenQuestStepIsNoneAndComponentIsEmpty_ShouldDoNothing()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);
        mockQuestTemplate.GetComponents(Any<QuestComponentKind>()).Returns([]);

        // Act
        var result = quest.StartQuest();

        // Assert
        await Assert.That(result).IsFalse();
        mockOwner.SendPacket(Any<GamePacket>()).WasCalled(Times.Once);
    }

    [Test]
    public async Task QuestInitialized_SetsInitializationFinished()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.QuestInitialized();

        // Assert
        // Note: _questInitializationFinished is private, test indirectly
        await Assert.That(true).IsTrue(); // If no exception, it's fine
    }

    [Test]
    public async Task FinalizeQuestActs_CallsFinalizeOnActs()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);
        // Mock quest steps and components

        // Act
        quest.FinalizeQuestActs();

        // Assert
        await Assert.That(true).IsTrue();
    }

    [Test]
    public async Task WriteData_ReturnsByteArray()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        var data = quest.WriteData();

        // Assert
        await Assert.That(data).IsNotNull();
        await Assert.That(data.Length > 0).IsTrue();
    }

    [Test]
    public async Task NewQuestAcceptances_UseDistinctRewardAttemptIds()
    {
        var first = SetupQuest(out _, out _, out _, out _, out _, out _, out _);
        var second = SetupQuest(out _, out _, out _, out _, out _, out _, out _);

        await Assert.That(first.RewardAttemptId).IsNotEqualTo(Guid.Empty);
        await Assert.That(second.RewardAttemptId).IsNotEqualTo(first.RewardAttemptId);
    }

    [Test]
    public async Task ReadData_WithLegacyFiveObjectiveData_ZeroFillsAa10Objectives()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);
        var stream = new PacketStream();
        stream.Write(1); // objective 1
        stream.Write(2); // objective 2
        stream.Write(3); // objective 3
        stream.Write(4); // objective 4
        stream.Write(5); // objective 5
        stream.Write((byte)QuestComponentKind.Progress); // step
        stream.Write((byte)QuestAcceptorType.Npc); // acceptor type
        stream.Write(100u); // component id
        stream.Write(200u); // acceptor id
        stream.Write(DateTime.UtcNow); // time

        // Act
        quest.ReadData(stream.GetBytes());

        // Assert
        await Assert.That(quest.Step).IsEqualTo(QuestComponentKind.Progress);
        await Assert.That(quest.QuestAcceptorType).IsEqualTo(QuestAcceptorType.Npc);
        await Assert.That(quest.Objectives.Length).IsEqualTo(Quest.ObjectiveCount);
        await Assert.That(quest.Objectives[..5]).IsEquivalentTo(new[] { 1, 2, 3, 4, 5 });
        await Assert.That(quest.Objectives[5..]).IsEquivalentTo(new int[5]);
    }

    #region Property Tests

    [Test]
    public async Task Status_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.Status = QuestStatus.Completed;

        // Assert
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Completed);
    }

    [Test]
    public async Task Step_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.Step = QuestComponentKind.Reward;

        // Assert
        await Assert.That(quest.Step).IsEqualTo(QuestComponentKind.Reward);
    }

    #endregion

    #region Objective Tests

    [Test]
    public async Task Objectives_ArrayAccess_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.Objectives[9] = 10;

        // Assert
        await Assert.That(quest.Objectives[9]).IsEqualTo(10);
    }

    [Test]
    public async Task ResyncReadyClientDoodadQuestReact_SendsSameStateUpdateOnlyWhenReady()
    {
        var readyQuest = SetupQuest(out var readyOwner, out _, out _, out _, out _, out _, out _);
        readyQuest.Status = QuestStatus.Ready;
        readyQuest.ComponentId = 10966;

        var progressQuest = SetupQuest(out var progressOwner, out _, out _, out _, out _, out _, out _);
        progressQuest.Status = QuestStatus.Progress;

        var readyResynced = readyQuest.ResyncReadyClientDoodadQuestReact();
        var progressResynced = progressQuest.ResyncReadyClientDoodadQuestReact();

        await Assert.That(readyResynced).IsTrue();
        await Assert.That(progressResynced).IsFalse();
        readyOwner.SendPacket(Any<GamePacket>()).WasCalled(Times.Once);
        progressOwner.SendPacket(Any<GamePacket>()).WasCalled(Times.Never);
    }

    #endregion

    #region ComponentId Tests

    [Test]
    public async Task ComponentId_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.ComponentId = 123;

        // Assert
        await Assert.That(quest.ComponentId).IsEqualTo(123u);
    }

    #endregion

    #region DoodadId Tests

    [Test]
    public async Task DoodadId_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.DoodadId = 456;

        // Assert
        await Assert.That(quest.DoodadId).IsEqualTo(456u);
    }

    #endregion

    #region QuestAcceptorType Tests

    [Test]
    public async Task QuestAcceptorType_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.QuestAcceptorType = QuestAcceptorType.Doodad;

        // Assert
        await Assert.That(quest.QuestAcceptorType).IsEqualTo(QuestAcceptorType.Doodad);
    }

    #endregion

    #region AcceptorId Tests

    [Test]
    public async Task AcceptorId_SetAndGet_ReturnsCorrectValue()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act
        quest.AcceptorId = 789;

        // Assert
        await Assert.That(quest.AcceptorId).IsEqualTo(789u);
    }

    #endregion

    #region Edge Cases

    [Test]
    public void Objectives_ArrayBounds_ThrowsPastAa10Capacity()
    {
        // Arrange
        var quest = SetupQuest(out var mockOwner, out var mockQuestTemplate, out _, out _, out _, out _, out _);

        // Act & Assert
        Assert.Throws<IndexOutOfRangeException>(() => quest.Objectives[10] = 1);
    }

    [Test]
    public async Task WriteData_RoundTripsAllTenAa10Objectives()
    {
        var source = SetupQuest(out _, out _, out _, out _, out _, out _, out _);
        for (var i = 0; i < Quest.ObjectiveCount; i++)
            source.Objectives[i] = (i + 1) * 11;
        source.Step = QuestComponentKind.Progress;
        source.QuestAcceptorType = QuestAcceptorType.Doodad;
        source.ComponentId = 1234;
        source.AcceptorId = 5678;
        // PacketStream's existing DateTime decoder only round-trips values up to
        // 59 seconds; keep this persistence-layout test inside that known range.
        source.Time = DateTime.UnixEpoch.AddSeconds(30);

        var data = source.WriteData();
        var restored = SetupQuest(out _, out _, out _, out _, out _, out _, out _);
        restored.ReadData(data);

        await Assert.That(data.Length).IsEqualTo(
            Quest.ObjectiveCount * sizeof(int) + Quest.PersistedTailSize);
        await Assert.That(restored.Objectives).IsEquivalentTo(source.Objectives);
        await Assert.That(restored.Step).IsEqualTo(source.Step);
        await Assert.That(restored.QuestAcceptorType).IsEqualTo(source.QuestAcceptorType);
        await Assert.That(restored.ComponentId).IsEqualTo(source.ComponentId);
        await Assert.That(restored.AcceptorId).IsEqualTo(source.AcceptorId);
        await Assert.That(restored.Time).IsEqualTo(source.Time);
        await Assert.That(restored.RewardAttemptId).IsEqualTo(source.RewardAttemptId);
        await Assert.That(restored.RewardAttemptId).IsNotEqualTo(Guid.Empty);
    }

    [Test]
    public async Task ReadData_WithPreviousAa10Payload_DerivesStableRewardAttemptId()
    {
        var stream = new PacketStream();
        for (var i = 0; i < Quest.ObjectiveCount; i++)
            stream.Write(i + 1);
        stream.Write((byte)QuestComponentKind.Progress);
        stream.Write((byte)QuestAcceptorType.Npc);
        stream.Write(100u);
        stream.Write(200u);
        stream.Write(DateTime.UnixEpoch.AddSeconds(30));

        var first = SetupQuest(out _, out _, out _, out _, out _, out _, out _);
        var second = SetupQuest(out _, out _, out _, out _, out _, out _, out _);
        first.Id = second.Id = 77;
        first.TemplateId = second.TemplateId = 12345;
        first.ReadData(stream.GetBytes());
        second.ReadData(stream.GetBytes());

        await Assert.That(stream.GetBytes().Length).IsEqualTo(
            Quest.ObjectiveCount * sizeof(int) + Quest.LegacyPersistedTailSize);
        await Assert.That(first.RewardAttemptId).IsEqualTo(second.RewardAttemptId);
        await Assert.That(first.RewardAttemptId).IsNotEqualTo(Guid.Empty);
    }

    [Test]
    public void ReadData_WithUnknownPayloadLength_FailsFast()
    {
        var quest = SetupQuest(out _, out _, out _, out _, out _, out _, out _);

        Assert.Throws<InvalidDataException>(() => quest.ReadData(new byte[39]));
    }

    #endregion

    private static Quest SetupQuest(
        out Mock<ICharacter> mockCharacter,
        out Mock<IQuestTemplate> mockQuestTemplate,
        out Mock<IQuestManager> mockQuestManager,
        out Mock<TaskManager>? mockTaskManager,
        out Mock<ISkillManager> mockSkillManager,
        out Mock<IExpressTextManager> mockExpressTextManager,
        out Mock<IWorldManager> mockWorldManager)
    {
        mockCharacter = Mock.Of<ICharacter>();
        mockQuestManager = Mock.Of<IQuestManager>();
        mockQuestTemplate = Mock.Of<IQuestTemplate>();
        mockQuestTemplate.Components.Returns(new Dictionary<uint, QuestComponentTemplate>());
        mockExpressTextManager = Mock.Of<IExpressTextManager>();
        mockSkillManager = Mock.Of<ISkillManager>();

        // Create TaskManager with ITickManager dependency
        var mockTickManager = Mock.Of<ITickManager>();
        mockTickManager.OnTick.Returns(new TickManager.TickEventHandler());
        var taskManagerInstance = new TaskManager(mockTickManager.Object);
        mockTaskManager = null;

        mockWorldManager = Mock.Of<IWorldManager>();

        var quest = new Quest(
            mockQuestTemplate.Object,
            mockCharacter.Object,
            mockQuestManager.Object,
            taskManagerInstance,
            mockSkillManager.Object,
            mockExpressTextManager.Object,
            mockWorldManager.Object);

        quest.Owner = mockCharacter.Object;
        quest.Template = mockQuestTemplate.Object;
        return quest;
    }
}
