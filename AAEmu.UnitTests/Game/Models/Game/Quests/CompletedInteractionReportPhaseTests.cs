using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.World;

namespace AAEmu.UnitTests.Game.Models.Game.Quests;

public class CompletedInteractionReportPhaseTests
{
    private static readonly DoodadFunc NativeUse = new()
    {
        GroupId = 39004, FuncId = 9972, FuncType = nameof(DoodadFuncUse), SkillId = 40100, NextPhase = 39007
    };
    private static readonly DoodadFunc NativeReport = new()
    {
        GroupId = 39007, FuncId = 1169, FuncType = nameof(DoodadFuncQuest), NextPhase = -1
    };

    private static IEnumerable<DoodadFunc> Functions(uint phase) => phase switch
    {
        39004 => [NativeUse], 39007 => [NativeReport], _ => []
    };
    private static DoodadFuncQuest Report(DoodadFunc _) => new() { QuestId = 9191, QuestKindId = 2 };

    [Test]
    public async Task AlcosReadyRestoresNativeUseDestinationFromPersistedCounter()
    {
        var quest = CreateQuest();
        // No live interaction, phase cache or event subscription is required after relog.
        var phase = quest.GetCompletedInteractionReportPhase(13447, Functions, Report);
        await Assert.That(phase).IsEqualTo(39007u);
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447, Functions, Report)).IsEqualTo(phase);
        await Assert.That(quest.Status).IsEqualTo(QuestStatus.Ready);
        await Assert.That(quest.Objectives[1]).IsEqualTo(1);
    }

    [Test]
    public async Task OtherCharacterAndDroppedOrIncompleteQuestCannotBorrowPhase()
    {
        var completed = CreateQuest();
        var other = CreateQuest();
        other.Objectives[1] = 0;
        await Assert.That(other.GetCompletedInteractionReportPhase(13447, Functions, Report)).IsEqualTo(0u);
        await Assert.That(completed.GetCompletedInteractionReportPhase(13308, Functions, Report)).IsEqualTo(0u);
        foreach (var status in new[] { QuestStatus.Progress, QuestStatus.Completed, QuestStatus.Dropped })
        {
            other.Status = status;
            other.Objectives[1] = 1;
            await Assert.That(other.GetCompletedInteractionReportPhase(13447, Functions, Report)).IsEqualTo(0u);
        }
    }

    [Test]
    public async Task RejectsWrongReportQuestAndAmbiguousOrMultiUseSource()
    {
        var quest = CreateQuest();
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447, Functions,
            _ => new DoodadFuncQuest { QuestId = 9193, QuestKindId = 2 })).IsEqualTo(0u);
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447, Functions,
            _ => new DoodadFuncQuest { QuestId = 9191, QuestKindId = 1 })).IsEqualTo(0u);
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447,
            p => p == 39004 ? [NativeUse, NativeUse] : Functions(p), Report)).IsEqualTo(0u);
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447,
            p => p == 39004 ? [new DoodadFunc { FuncType = nameof(DoodadFuncUse), SkillId = 40100,
                NextPhase = 39007, Count = 2 }] : Functions(p), Report)).IsEqualTo(0u);
    }

    [Test]
    public async Task RequiresExactNativeHighlightAndUseObjective()
    {
        var quest = CreateQuest();
        var objective = (QuestActObjInteraction)quest.Template.Components[40083].ActTemplates[0];
        objective.HighlightDoodadPhase = -1;
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447, Functions, Report)).IsEqualTo(0u);
        objective.HighlightDoodadPhase = 39004;
        objective.HighlightDoodadId = 13308;
        await Assert.That(quest.GetCompletedInteractionReportPhase(13447, Functions, Report)).IsEqualTo(0u);
    }

    [Test]
    public async Task PersonalPhasePacketKeepsSharedProxyUntouchedAndDoesNotLeakSharedData()
    {
        var doodad = new Doodad { ObjId = 101267, Data = 42, ItemTemplateId = 99 };
        // Populate a snapshot without starting the world's phase functions in this wire test.
        typeof(Doodad).GetField("_funcGroupId", System.Reflection.BindingFlags.Instance |
            System.Reflection.BindingFlags.NonPublic)!.SetValue(doodad, 38981u);
        var personal = new SCDoodadPhaseChangedPacket(doodad, 39007);
        var stream = new PacketStream();
        personal.Write(stream);
        stream.Pos = 0;
        await Assert.That(stream.ReadBc()).IsEqualTo(101267u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(39007u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(stream.ReadInt32()).IsEqualTo(-1);
        await Assert.That(stream.ReadUInt32()).IsEqualTo(0u);
        await Assert.That(stream.ReadBoolean()).IsFalse();
        await Assert.That(stream.HasBytes).IsFalse();
        await Assert.That(doodad.FuncGroupId).IsEqualTo(38981u);
        await Assert.That(doodad.Data).IsEqualTo(42);

        var shared = new PacketStream();
        new SCDoodadPhaseChangedPacket(doodad).Write(shared);
        shared.Pos = 0;
        shared.ReadBc();
        await Assert.That(shared.ReadUInt32()).IsEqualTo(38981u);
        await Assert.That(shared.ReadUInt32()).IsEqualTo(42u);
    }

    private static Quest CreateQuest()
    {
        var template = new QuestTemplate { Id = 9191 };
        var quest = new Quest(template, Mock.Of<ICharacter>().Object, Mock.Of<IQuestManager>().Object,
            Mock.Of<ITaskManager>().Object, Mock.Of<ISkillManager>().Object,
            Mock.Of<IExpressTextManager>().Object, Mock.Of<IWorldManager>().Object);
        var progress = new QuestComponentTemplate(template) { Id = 40083, KindId = QuestComponentKind.Progress };
        progress.ActTemplates.Add(new QuestActObjInteraction(progress)
        {
            DoodadId = 13447, HighlightDoodadId = 13447, HighlightDoodadPhase = 39004,
            WorldInteractionId = WorldInteractionType.Use, Count = 1, ThisComponentObjectiveIndex = 1
        });
        template.Components.Add(progress.Id, progress);
        var ready = new QuestComponentTemplate(template) { Id = 39922, KindId = QuestComponentKind.Ready };
        ready.ActTemplates.Add(new QuestActConReportDoodad(ready) { DoodadId = 13447 });
        template.Components.Add(ready.Id, ready);
        quest.Status = QuestStatus.Ready;
        quest.Objectives[1] = 1;
        return quest;
    }
}
