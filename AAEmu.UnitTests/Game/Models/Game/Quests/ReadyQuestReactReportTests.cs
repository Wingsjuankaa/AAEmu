using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

[NotInParallel]
public class ReadyQuestReactReportTests
{
    private object _previous;
    private object _previousQuests;
    private static FieldInfo QuestSingletonField => typeof(Singleton<QuestManager>)
        .GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
    private readonly DoodadFuncQuest _report = new() { QuestId = 10159, QuestKindId = 2 };
    private static FieldInfo SingletonField => typeof(Singleton<DoodadManager>)
        .GetField("s_instance", BindingFlags.NonPublic | BindingFlags.Static)!;
    private static void Set(object obj, string name, object value) => obj.GetType()
        .GetField(name, BindingFlags.NonPublic | BindingFlags.Instance)!.SetValue(obj, value);

    [Before(Test)]
    public void Setup()
    {
        _previous = SingletonField.GetValue(null);
        _previousQuests = QuestSingletonField.GetValue(null);
        QuestSingletonField.SetValue(null, new QuestManager(Mock.Of<ITaskManager>().Object, Mock.Of<IZoneManager>().Object));
        var manager = new DoodadManager(null, null, null, null, null, null);
        Set(manager, "_phaseFuncs", new Dictionary<uint, List<DoodadPhaseFunc>>
        {
            [45390] = [new() { FuncId = 2300, FuncType = nameof(DoodadFuncQuestReact) }],
            [45391] = [new() { FuncId = 2312, FuncType = nameof(DoodadFuncQuestReact) }]
        });
        Set(manager, "_phaseFuncTemplates", new Dictionary<string, Dictionary<uint, DoodadPhaseFuncTemplate>>
        {
            [nameof(DoodadFuncQuestReact)] = new()
            {
                [2300] = new DoodadFuncQuestReact { QuestId = 10038, QuestStatus = QuestStatus.Completed, NextPhase = 45391 },
                [2312] = new DoodadFuncQuestReact { QuestId = 10159, QuestStatus = QuestStatus.Ready, NextPhase = 45394 }
            }
        });
        Set(manager, "_funcsByGroups", new Dictionary<uint, List<DoodadFunc>>
        {
            [45394] = [new() { FuncId = 2196, FuncType = nameof(DoodadFuncQuest) }]
        });
        Set(manager, "_funcTemplates", new Dictionary<string, Dictionary<uint, DoodadFuncTemplate>>
        {
            [nameof(DoodadFuncQuest)] = new() { [2196] = _report }
        });
        SingletonField.SetValue(null, manager);
    }

    [After(Test)]
    public void Cleanup()
    {
        SingletonField.SetValue(null, _previous);
        QuestSingletonField.SetValue(null, _previousQuests);
    }

    private static (Character, Quest, Doodad, QuestActConReportDoodad) Create()
    {
        var owner = new Character(null);
        owner.Quests = new CharacterQuests(owner);
        owner.Quests.SetCompletedQuestFlag(10038, true);
        var template = new QuestTemplate { Id = 10159 };
        var quest = new Quest(template, owner, Mock.Of<IQuestManager>().Object,
            Mock.Of<ITaskManager>().Object, Mock.Of<ISkillManager>().Object,
            Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var progress = new QuestComponentTemplate(template) { Id = 44188, KindId = QuestComponentKind.Progress };
        progress.ActTemplates.Add(new QuestActObjInteraction(progress)
        {
            DoodadId = 15353, HighlightDoodadPhase = -1, WorldInteractionId = WorldInteractionType.Use,
            Count = 1, ThisComponentObjectiveIndex = 0
        });
        var ready = new QuestComponentTemplate(template) { Id = 44189, KindId = QuestComponentKind.Ready };
        var report = new QuestActConReportDoodad(ready) { DoodadId = 15353 };
        ready.ActTemplates.Add(report);
        template.Components.Add(progress.Id, progress);
        template.Components.Add(ready.Id, ready);
        owner.Quests.ActiveQuests.Add(10159, quest);
        quest.Status = QuestStatus.Ready;
        quest.Objectives[0] = 1;
        var doodad = new Doodad { ObjId = 101639, TemplateId = 15353,
            Template = new DoodadTemplate { ClientDoodad = true, OnceOneMan = true } };
        Set(doodad, "_funcGroupId", 45390u);
        return (owner, quest, doodad, report);
    }

    [Test]
    public async Task CompletedUseWithoutHighlightedPhaseResolvesNativeReadyReport()
    {
        var (owner, _, doodad, _) = Create();
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out var phase)).IsTrue();
        await Assert.That(phase).IsEqualTo(45394u);
        await Assert.That(doodad.FuncGroupId).IsEqualTo(45390u);
    }

    [Test]
    public async Task CompletedCounterBeforeQueuedReadyEvaluationDoesNotPublishReport()
    {
        var (owner, quest, doodad, _) = Create();
        quest.Status = QuestStatus.Progress; // counter is already 1, evaluation has not run yet
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
        quest.Status = QuestStatus.Ready;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out var phase)).IsTrue();
        await Assert.That(phase).IsEqualTo(45394u);
        quest.Status = QuestStatus.Completed;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
    }

    [Test]
    public async Task QueuedEvaluationSendsReadyContextThenPersonalPhaseOnlyOnce()
    {
        var (owner, quest, doodad, _) = Create();
        var sent = new List<byte[]>();
        var session = Mock.Of<ISession>();
        session.SendPacket(Any<byte[]>()).Callback((byte[] bytes) => sent.Add(bytes));
        owner.Connection = new GameConnection(session.Object);
        var region = new Region(null, 0, 0, 0);
        Set(region, "_neighbors", new[] { region });
        doodad.Transform = null;
        region.AddObject(doodad);
        owner.Region = region;
        quest.CreateQuestSteps();
        foreach (var component in quest.QuestSteps.Values.SelectMany(step => step.Components.Values))
            foreach (var act in component.Template.ActTemplates)
                component.Acts.Add(new QuestAct(component, act));
        quest.Step = QuestComponentKind.Progress;
        quest.Status = QuestStatus.Progress;
        quest.QuestInitialized();
        sent.Clear();

        quest.RunCurrentStep();
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Ready);
        ushort Opcode(byte[] bytes)
        {
            var stream = new PacketStream(bytes);
            stream.ReadUInt16(); // frame length
            stream.ReadByte(); // signature
            stream.ReadByte(); // level 1
            stream.ReadByte(); stream.ReadByte(); // crc/counter placeholders
            return stream.ReadUInt16();
        }
        await Assert.That(sent.Select(Opcode).ToArray()).IsEquivalentTo(new ushort[]
            { SCOffsets.SCQuestContextUpdatedPacket, SCOffsets.SCDoodadPhaseChangedPacket });
        await Assert.That(Opcode(sent[0])).IsEqualTo(SCOffsets.SCQuestContextUpdatedPacket);
        await Assert.That(Opcode(sent[1])).IsEqualTo(SCOffsets.SCDoodadPhaseChangedPacket);
        sent.Clear();
        quest.RunCurrentStep(); // still Ready, awaiting the user's report
        await Assert.That(sent.Any(bytes => Opcode(bytes) == SCOffsets.SCDoodadPhaseChangedPacket)).IsFalse();
        await Assert.That(doodad.FuncGroupId).IsEqualTo(45390u);
    }

    [Test]
    public async Task RequiresExactQuestReporterAndPersonalActor()
    {
        var (owner, _, doodad, report) = Create();
        _report.QuestId = 10039;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
        _report.QuestId = 10159;
        _report.QuestKindId = 1;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
        _report.QuestKindId = 2;
        report.DoodadId = 14955;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
        report.DoodadId = 15353;
        doodad.Template.ClientDoodad = false;
        await Assert.That(doodad.TryGetCompletedInteractionReportPhase(owner, out _)).IsFalse();
    }
}
