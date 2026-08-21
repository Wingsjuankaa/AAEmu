using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class CharacterQuestsTests
{
    [Test]
    public async Task TryResyncReadyClientDoodadQuestReacts_ReplaysCurrentEnterOnly()
    {
        var owner = Mock.Of<ICharacter>();
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "Tester" };
        var characterQuests = new CharacterQuests(character);
        var readyQuest = CreateQuest(owner);
        readyQuest.Status = QuestStatus.Ready;
        readyQuest.ComponentId = 10966;
        var progressQuest = CreateQuest(owner);
        progressQuest.Status = QuestStatus.Progress;
        characterQuests.ActiveQuests.Add(2532, readyQuest);
        characterQuests.ActiveQuests.Add(2256, progressQuest);

        var edgeVersion = characterQuests.MarkClientDoodadQuestReactEdge();
        var resynced = characterQuests.TryResyncReadyClientDoodadQuestReacts(328, edgeVersion);

        await Assert.That(resynced).IsEqualTo(1);
        owner.SendPacket(Any<GamePacket>()).WasCalled(Times.Once);
    }

    [Test]
    public async Task TryResyncReadyClientDoodadQuestReacts_IgnoresStaleEnterAfterNewerEnter()
    {
        var owner = Mock.Of<ICharacter>();
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "Tester" };
        var characterQuests = new CharacterQuests(character);
        var readyQuest = CreateQuest(owner);
        readyQuest.Status = QuestStatus.Ready;
        characterQuests.ActiveQuests.Add(2532, readyQuest);

        var staleEnterVersion = characterQuests.MarkClientDoodadQuestReactEdge();
        characterQuests.MarkClientDoodadQuestReactEdge();

        var resynced = characterQuests.TryResyncReadyClientDoodadQuestReacts(328, staleEnterVersion);

        await Assert.That(resynced).IsEqualTo(0);
        owner.SendPacket(Any<GamePacket>()).WasCalled(Times.Never);
    }

    [Test]
    public async Task TryResyncReadyClientDoodadQuestReacts_IgnoresLeaveSentinel()
    {
        var owner = Mock.Of<ICharacter>();
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "Tester" };
        var characterQuests = new CharacterQuests(character);
        var readyQuest = CreateQuest(owner);
        readyQuest.Status = QuestStatus.Ready;
        characterQuests.ActiveQuests.Add(2532, readyQuest);

        var edgeVersion = characterQuests.MarkClientDoodadQuestReactEdge();
        var resynced = characterQuests.TryResyncReadyClientDoodadQuestReacts(0, edgeVersion);

        await Assert.That(resynced).IsEqualTo(0);
        owner.SendPacket(Any<GamePacket>()).WasCalled(Times.Never);
    }

    private static Quest CreateQuest(Mock<ICharacter> owner)
    {
        var template = Mock.Of<IQuestTemplate>();
        template.Components.Returns(new Dictionary<uint, QuestComponentTemplate>());
        var questManager = Mock.Of<IQuestManager>();
        var tickManager = Mock.Of<ITickManager>();
        tickManager.OnTick.Returns(new TickManager.TickEventHandler());

        return new Quest(
            template.Object,
            owner.Object,
            questManager.Object,
            new TaskManager(tickManager.Object),
            Mock.Of<ISkillManager>().Object,
            Mock.Of<IExpressTextManager>().Object,
            Mock.Of<IWorldManager>().Object)
        {
            Owner = owner.Object,
            Template = template.Object
        };
    }
}
