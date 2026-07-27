using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Quests.Acts;
using Xunit;

namespace AAEmu.Tests
{
    public class QuestCompletionGuardTests
    {
        [Fact]
        public void RewardItemEventsAreIgnoredWhileQuestIsCompleting()
        {
            var quest = new Quest
            {
                IsCompleting = true,
                Status = QuestStatus.Ready
            };

            quest.OnItemGather(null, 1);
            quest.OnItemUse(null);

            Assert.Equal(QuestStatus.Ready, quest.Status);
        }

        [Fact]
        public void RewardItemEventsAreIgnoredAfterQuestIsCompleted()
        {
            var quest = new Quest
            {
                Status = QuestStatus.Completed
            };

            quest.OnItemGather(null, 1);
            quest.OnItemUse(null);

            Assert.Equal(QuestStatus.Completed, quest.Status);
        }

        [Fact]
        public void RewardEventsAreIgnoredWhileQuestUpdateIsRunning()
        {
            var quest = new Quest
            {
                IsUpdating = true,
                Status = QuestStatus.Ready,
                Step = QuestComponentKind.Reward
            };

            quest.OnItemGather(null, 1);
            quest.OnItemUse(null);
            quest.OnLevelUp();

            Assert.Equal(QuestStatus.Ready, quest.Status);
            Assert.Equal(QuestComponentKind.Reward, quest.Step);
        }

        [Fact]
        public void CompletedProgressStopsAtRealReadyComponent()
        {
            var template = new AAEmu.Game.Models.Game.Quests.Templates.QuestTemplate
            {
                Id = 2255
            };
            template.Components.Add(
                9943,
                new QuestComponent
                {
                    Id = 9943,
                    KindId = QuestComponentKind.Progress
                });
            template.Components.Add(
                9944,
                new QuestComponent
                {
                    Id = 9944,
                    KindId = QuestComponentKind.Ready
                });
            var quest = new Quest(template)
            {
                Status = QuestStatus.Progress,
                Step = QuestComponentKind.Progress,
                ComponentId = 9943
            };

            Assert.True(quest.TransitionCompletedProgressToReady());
            Assert.Equal(QuestStatus.Ready, quest.Status);
            Assert.Equal(QuestComponentKind.Ready, quest.Step);
            Assert.Equal(9944u, quest.ComponentId);
        }

        [Theory]
        [InlineData(false, false, ItemDefinitionCoverageState.Unknown, false)]
        [InlineData(false, true, ItemDefinitionCoverageState.Complete, false)]
        [InlineData(true, false, ItemDefinitionCoverageState.Unknown, true)]
        [InlineData(true, true, ItemDefinitionCoverageState.Unknown, false)]
        [InlineData(true, true, ItemDefinitionCoverageState.CatalogOnly, false)]
        [InlineData(true, true, ItemDefinitionCoverageState.Blocked, false)]
        [InlineData(true, true, ItemDefinitionCoverageState.Complete, true)]
        public void QuestStartSupplyRequiresCreatableItemDefinition(
            bool itemTemplateExists,
            bool nativeCatalogueAvailable,
            ItemDefinitionCoverageState coverageState,
            bool expected)
        {
            Assert.Equal(
                expected,
                QuestStartDependencyGuard.EvaluateSupplyItemDefinition(
                    itemTemplateExists,
                    nativeCatalogueAvailable,
                    coverageState));
        }

        [Fact]
        public void ClientDoodadNpcProxyMatchesNativeNpcTarget()
        {
            var doodadTemplate = CreateMarianProxyTemplate();
            var doodad = new Doodad
            {
                TemplateId = 14074,
                Template = doodadTemplate
            };

            Assert.True(Quest.MatchesNpcTarget(doodad, 10581));
            Assert.False(Quest.MatchesNpcTarget(doodad, 10646));
        }

        [Fact]
        public void AcceptNpcActAllowsMatchingClientDoodadProxy()
        {
            var character = new Character(null);
            var quest = new Quest
            {
                InteractionTarget = new Doodad
                {
                    TemplateId = 14074,
                    Template = CreateMarianProxyTemplate()
                }
            };
            var act = new QuestActConAcceptNpc
            {
                NpcId = 10581
            };

            Assert.True(act.Use(character, quest, 0));
            Assert.Equal(QuestAcceptorType.Npc, quest.QuestAcceptorType);
            Assert.Equal(10581u, quest.AcceptorType);
        }

        [Fact]
        public void ReportNpcActAllowsMatchingClientDoodadProxy()
        {
            var character = new Character(null);
            var quest = new Quest
            {
                InteractionTarget = new Doodad
                {
                    TemplateId = 14074,
                    Template = CreateMarianProxyTemplate()
                }
            };
            var act = new QuestActConReportNpc
            {
                NpcId = 10581
            };

            Assert.True(act.Use(character, quest, 0));
        }

        private static DoodadTemplate CreateMarianProxyTemplate()
        {
            var template = new DoodadTemplate
            {
                Id = 14074,
                ClientDoodad = true
            };
            template.FuncGroups.Add(
                new DoodadFuncGroups
                {
                    Id = 41496,
                    GroupKindId = DoodadFuncGroups.DoodadFuncGroupKind.Normal,
                    Model = "npctype://10581"
                });
            return template;
        }
    }
}
