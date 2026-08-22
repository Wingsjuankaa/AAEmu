using System.Net;
using System.Net.Sockets;

using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class CharacterQuestsTests
{
    private sealed class RecordingSession : ISession
    {
        public List<byte[]> Packets { get; } = [];
        public IPAddress Ip => IPAddress.Loopback;
        public uint SessionId => 1;
        public Socket Socket => null!;

        public void SendPacket(byte[] packet) => Packets.Add(packet);
        public void AddAttribute(string name, object attribute) { }
        public object GetAttribute(string name) => null;
        public void ClearAttribute(string name) { }
        public void Close() { }
    }

    [Test]
    public async Task SendInitialState_InitializesQuestNotifierAfterQuestLists()
    {
        var session = new RecordingSession();
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "Tester" };
        character.Connection = new GameConnection(session);
        var characterQuests = new CharacterQuests(character);

        characterQuests.SendInitialState();

        await Assert.That(session.Packets.Count).IsEqualTo(3);
        await Assert.That(BitConverter.ToUInt16(session.Packets[0], 6)).IsEqualTo((ushort)0x132);
        await Assert.That(BitConverter.ToUInt16(session.Packets[1], 6)).IsEqualTo((ushort)0x133);
        await Assert.That(BitConverter.ToUInt16(session.Packets[2], 6)).IsEqualTo((ushort)0x287);
        await Assert.That(session.Packets[2][8]).IsEqualTo((byte)1);
    }

    [Test]
    public async Task QuestCompletionScope_SatisfiesRequirementsWithoutPersistingTheBit()
    {
        const uint questId = 6701;
        var character = new Character(new UnitCustomModelParams()) { Id = 42, Name = "Tester" };
        var characterQuests = new CharacterQuests(character);
        character.Quests = characterQuests;
        var completeRequirement = new UnitReqs
        {
            KindType = UnitReqsKindType.CompleteQuestContext,
            Value1 = questId
        };
        var exceptCompleteRequirement = new UnitReqs
        {
            KindType = UnitReqsKindType.ExceptCompleteQuestContext,
            Value1 = questId
        };

        await Assert.That(characterQuests.HasQuestCompleted(questId)).IsFalse();
        await Assert.That(characterQuests.HasQuestCompletedOrCompleting(questId)).IsFalse();
        await Assert.That(completeRequirement.Validate(character, character).ResultKey)
            .IsNotEqualTo(SkillResultKeys.ok);
        await Assert.That(exceptCompleteRequirement.Validate(character, character).ResultKey)
            .IsEqualTo(SkillResultKeys.ok);

        using (characterQuests.BeginQuestCompletion(questId))
        {
            await Assert.That(characterQuests.HasQuestCompleted(questId)).IsFalse();
            await Assert.That(characterQuests.HasQuestCompletedOrCompleting(questId)).IsTrue();
            await Assert.That(completeRequirement.Validate(character, character).ResultKey)
                .IsEqualTo(SkillResultKeys.ok);
            await Assert.That(exceptCompleteRequirement.Validate(character, character).ResultKey)
                .IsNotEqualTo(SkillResultKeys.ok);

            using (characterQuests.BeginQuestCompletion(questId))
                await Assert.That(characterQuests.HasQuestCompletedOrCompleting(questId)).IsTrue();

            await Assert.That(characterQuests.HasQuestCompletedOrCompleting(questId)).IsTrue();
        }

        await Assert.That(characterQuests.HasQuestCompletedOrCompleting(questId)).IsFalse();
    }

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
