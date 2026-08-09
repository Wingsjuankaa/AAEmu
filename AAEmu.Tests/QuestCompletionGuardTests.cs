using System;

using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
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
        public void ItemEventsCannotMoveReadyQuestBackToProgress()
        {
            var quest = new Quest
            {
                Status = QuestStatus.Ready,
                Step = QuestComponentKind.Ready
            };

            quest.OnItemGather(null, 1);
            quest.OnItemUse(null);

            Assert.Equal(QuestStatus.Ready, quest.Status);
            Assert.Equal(QuestComponentKind.Ready, quest.Step);
        }

        [Theory]
        [InlineData(1, 0, 0, 1, true)]
        [InlineData(1, 1, 0, 1, false)]
        [InlineData(1, 0, 1, 1, false)]
        [InlineData(2, 0, 0, 2, true)]
        [InlineData(2, 1, 1, 2, false)]
        [InlineData(0, 0, 0, 1, false)]
        public void QuestLootRequiresBothObjectiveAndInventoryCapacity(
            int required,
            int objective,
            int carried,
            int incoming,
            bool expected)
        {
            Assert.Equal(
                expected,
                Quest.HasRemainingItemGather(
                    required,
                    objective,
                    carried,
                    incoming));
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
        [InlineData(41999, 41999, false)]
        [InlineData(0, 41999, true)]
        [InlineData(16001, 41999, true)]
        [InlineData(41999, 0, false)]
        public void DoodadUseDoesNotRescheduleItsTriggerSkill(
            uint triggerSkillId,
            uint configuredSkillId,
            bool expected)
        {
            Assert.Equal(
                expected,
                DoodadFuncUse.ShouldScheduleSkill(triggerSkillId, configuredSkillId));
        }

        [Fact]
        public void PersistedReadyQuestBeyondRewardBoundaryReturnsToNativeReadyComponent()
        {
            var template = new AAEmu.Game.Models.Game.Quests.Templates.QuestTemplate
            {
                Id = 4411
            };
            template.Components.Add(
                41261,
                new QuestComponent
                {
                    Id = 41261,
                    KindId = QuestComponentKind.Progress
                });
            template.Components.Add(
                19170,
                new QuestComponent
                {
                    Id = 19170,
                    KindId = QuestComponentKind.Ready
                });
            var quest = new Quest(template)
            {
                Status = QuestStatus.Ready,
                Step = (QuestComponentKind)9,
                ComponentId = 19171
            };

            Assert.True(quest.NormalizePersistedReadyBoundary());
            Assert.Equal(QuestStatus.Ready, quest.Status);
            Assert.Equal(QuestComponentKind.Ready, quest.Step);
            Assert.Equal(19170u, quest.ComponentId);
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

        [Theory]
        [InlineData(0, 0, true)]
        [InlineData(1, 0, false)]
        [InlineData(0, 3, false)]
        [InlineData(1, 3, true)]
        [InlineData(3, 3, true)]
        [InlineData(4, 3, false)]
        public void SelectiveQuestRewardRequiresOneBasedNativeSelection(
            int selected,
            int selectiveRewardCount,
            bool expected)
        {
            Assert.Equal(
                expected,
                QuestRewardDependencyGuard.IsValidSelection(
                    selected,
                    selectiveRewardCount));
        }

        [Theory]
        [InlineData(false, false, ItemDefinitionCoverageState.Unknown, false, false)]
        [InlineData(true, false, ItemDefinitionCoverageState.Unknown, false, true)]
        [InlineData(true, true, ItemDefinitionCoverageState.Complete, false, true)]
        [InlineData(true, true, ItemDefinitionCoverageState.PhaseACandidate, false, false)]
        [InlineData(true, true, ItemDefinitionCoverageState.PhaseACandidate, true, true)]
        [InlineData(true, true, ItemDefinitionCoverageState.Blocked, true, false)]
        public void QuestRewardRequiresCreatableItemDefinition(
            bool itemTemplateExists,
            bool nativeCatalogueAvailable,
            ItemDefinitionCoverageState coverageState,
            bool phaseACandidateCreationAllowed,
            bool expected)
        {
            Assert.Equal(
                expected,
                QuestRewardDependencyGuard.EvaluateRewardItemDefinition(
                    itemTemplateExists,
                    nativeCatalogueAvailable,
                    coverageState,
                    phaseACandidateCreationAllowed));
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

        [Fact]
        public void AcceptSphereActStartsQuestAndRecordsTheSphere()
        {
            var quest = new Quest();
            var act = new QuestActConAcceptSphere
            {
                SphereId = 2321
            };

            Assert.True(act.Use(new Character(null), quest, 0));
            Assert.Equal(QuestAcceptorType.Sphere, quest.QuestAcceptorType);
            Assert.Equal(2321u, quest.AcceptorType);
        }

        [Fact]
        public void EventDrivenObjectivesUseOnlyValidatedCounters()
        {
            var quest = new Quest();
            var cinema = new QuestActObjCinema { CinemaId = 163 };
            var sphere = new QuestActObjSphere { SphereId = 1415 };
            var talk = new QuestActObjTalk { NpcId = 10988 };

            Assert.False(cinema.Use(null, quest, 0));
            Assert.False(sphere.Use(null, quest, 0));
            Assert.False(talk.Use(null, quest, 0));
            Assert.True(cinema.Use(null, quest, 1));
            Assert.True(sphere.Use(null, quest, 1));
            Assert.True(talk.Use(null, quest, 1));
        }

        [Fact]
        public void NativeV2CountPredicatesRespectCountAndScore()
        {
            Assert.False(Quest.MeetsQuestActCount(0, 1, 0));
            Assert.True(Quest.MeetsQuestActCount(3, 3, 0));
            Assert.False(Quest.MeetsQuestActCount(2, 3, 0));
            Assert.True(Quest.MeetsQuestActCount(2, 3, 6));
            Assert.False(Quest.MeetsQuestActCount(1, 3, 6));
            Assert.False(Quest.MeetsQuestActCount(5, 0, 0));
        }

        [Fact]
        public void NativeV2EffectAndDoodadPhaseActsRequireValidatedEvents()
        {
            var quest = new Quest
            {
                Template = new AAEmu.Game.Models.Game.Quests.Templates.QuestTemplate()
            };
            var effect = new QuestActObjEffectFire
            {
                EffectId = 42069,
                Count = 2,
                TeamShare = false
            };
            var phase = new QuestActObjDoodadPhaseCheck
            {
                DoodadId = 13378,
                Phase1 = 40123,
                Phase2 = 0
            };

            Assert.False(effect.Use(null, quest, 0));
            Assert.False(effect.Use(null, quest, 1));
            Assert.True(effect.Use(null, quest, 2));
            Assert.False(phase.Use(null, quest, 0));
            Assert.True(phase.Use(null, quest, 1));
        }

        [Fact]
        public void NativeV2ComponentAcceptRequiresExactSelfOrMaterializedSuccessor()
        {
            Assert.False(QuestActConAcceptComponent.MatchesContextReference(0, 10303, true));
            Assert.False(QuestActConAcceptComponent.MatchesContextReference(10303, 0, true));
            Assert.True(QuestActConAcceptComponent.MatchesContextReference(10303, 10303, false));
            Assert.False(QuestActConAcceptComponent.MatchesContextReference(8536, 8516, false));
            Assert.True(QuestActConAcceptComponent.MatchesContextReference(8536, 8516, true));
        }

        [Fact]
        public void QuestTimerDeadlineSurvivesPersistenceRoundTrip()
        {
            var deadline = DateTimeOffset.FromUnixTimeSeconds(
                DateTimeOffset.UtcNow.ToUnixTimeSeconds() + 180).UtcDateTime;
            var source = new Quest
            {
                Step = QuestComponentKind.Progress,
                QuestAcceptorType = QuestAcceptorType.Npc,
                ComponentId = 1234,
                AcceptorType = 5678,
                Time = deadline
            };
            var restored = new Quest();

            restored.ReadData(source.WriteData());

            Assert.Equal(deadline, restored.Time);
            Assert.True(restored.LeftTime > 0);
        }

        [Fact]
        public void TalkEventRequiresExactNativeQuestComponentActAndNpc()
        {
            var quest = new Quest
            {
                TemplateId = 2486,
                Status = QuestStatus.Progress,
                Step = QuestComponentKind.Progress
            };
            var component = new QuestComponent
            {
                Id = 10745,
                KindId = QuestComponentKind.Progress
            };
            var act = new QuestAct
            {
                Id = 26178,
                ComponentId = 10745,
                DetailType = nameof(QuestActObjTalk)
            };
            var talk = new QuestActObjTalk { NpcId = 10586 };

            Assert.True(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2486, 10745, 26178, 10586));
            Assert.False(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2487, 10745, 26178, 10586));
            Assert.False(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2486, 10746, 26178, 10586));
            Assert.False(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2486, 10745, 26179, 10586));
            Assert.False(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2486, 10745, 26178, 10585));

            quest.Status = QuestStatus.Ready;
            Assert.False(Quest.MatchesTalkEventContext(
                quest, component, act, talk, 2486, 10745, 26178, 10586));
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
