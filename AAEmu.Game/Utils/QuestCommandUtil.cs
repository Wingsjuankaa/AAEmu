using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using NLog;

namespace AAEmu.Game.Utils
{
    public class QuestCommandUtil
    {
        private static readonly Logger Log = LogManager.GetCurrentClassLogger();

        private static void ReportQuestState(Character character, uint questId)
        {
            var active = character.Quests.HasQuest(questId);
            var completed = character.Quests.IsQuestComplete(questId);
            if (active)
            {
                var quest = character.Quests.Quests[questId];
                character.SendMessage(
                    "[QuestProbe] result=ACTIVE quest={0} step={1} status={2} component={3}",
                    questId,
                    quest.Step,
                    quest.Status,
                    quest.ComponentId);
                Log.Info(
                    "[QuestProbe] character={0} quest={1} result=ACTIVE step={2} status={3} component={4}",
                    character.Name,
                    questId,
                    quest.Step,
                    quest.Status,
                    quest.ComponentId);
                return;
            }

            character.SendMessage(
                "[QuestProbe] result=NOT_ACTIVE quest={0} completed={1}",
                questId,
                completed);
            Log.Warn(
                "[QuestProbe] character={0} quest={1} result=NOT_ACTIVE completed={2}",
                character.Name,
                questId,
                completed);
        }

        private static void Diagnose(Character character, uint questId)
        {
            var template = QuestManager.Instance.GetTemplate(questId);
            if (template == null)
            {
                character.SendMessage("[QuestProbe] quest={0} template=MISSING", questId);
                Log.Warn(
                    "[QuestProbe] character={0} quest={1} template=MISSING",
                    character.Name,
                    questId);
                return;
            }

            var factionId = character.Faction?.Id ?? 0;
            var factionChain = FactionManager.Instance.GetMotherChain(factionId);
            var targetNpc = character.CurrentTarget as Npc;
            character.SendMessage(
                "[QuestProbe] quest={0} template=OK active={1} completed={2}",
                questId,
                character.Quests.HasQuest(questId),
                character.Quests.IsQuestComplete(questId));
            character.SendMessage(
                "[QuestProbe] player level={0} race={1} zoneKey={2} factionChain={3}",
                character.Level,
                (byte)character.Race,
                character.Transform.ZoneId,
                string.Join(">", factionChain));
            character.SendMessage(
                "[QuestProbe] target obj={0} npcTemplate={1}",
                targetNpc?.ObjId ?? 0,
                targetNpc?.TemplateId ?? 0);
            character.SendMessage(
                "[QuestProbe] template level={0} zoneId={1} repeatable={2} successive={3}",
                template.Level,
                template.ZoneId,
                template.Repeatable,
                template.Successive);

            var knownRequirementsPass = true;
            var unknownRequirements = false;
            foreach (var component in template.Components.Values.OrderBy(x => x.Id))
            {
                character.SendMessage(
                    "[QuestProbe] component={0} step={1} orReqs={2}",
                    component.Id,
                    component.KindId,
                    component.OrUnitReqs);
                foreach (var requirement in
                         QuestManager.Instance.GetComponentRequirements(component.Id))
                {
                    if (requirement.KindId == 56)
                    {
                        var pass = FactionManager.Instance.IsInFactionHierarchy(
                            factionId,
                            requirement.Value1);
                        knownRequirementsPass &= pass;
                        character.SendMessage(
                            "[QuestProbe] req kind=56 faction={0} result={1}",
                            requirement.Value1,
                            pass ? "PASS" : "FAIL");
                    }
                    else
                    {
                        unknownRequirements = true;
                        character.SendMessage(
                            "[QuestProbe] req kind={0} values={1}/{2}/{3} result=UNKNOWN",
                            requirement.KindId,
                            requirement.Value1,
                            requirement.Value2,
                            requirement.Value3);
                    }
                }

                foreach (var act in QuestManager.Instance.GetActs(component.Id))
                {
                    if (act.DetailType == "QuestActConAcceptNpc")
                    {
                        var accept = act.GetTemplate<QuestActConAcceptNpc>();
                        var expectedNpc = accept?.NpcId ?? 0;
                        var pass = targetNpc != null &&
                                   targetNpc.TemplateId == expectedNpc;
                        character.SendMessage(
                            "[QuestProbe] acceptNpc expected={0} targetMatch={1}",
                            expectedNpc,
                            pass ? "PASS" : "FAIL");
                    }
                    else if (act.DetailType == "QuestActConReportNpc")
                    {
                        var report = act.GetTemplate<QuestActConReportNpc>();
                        var expectedNpc = report?.NpcId ?? 0;
                        var pass = targetNpc != null &&
                                   targetNpc.TemplateId == expectedNpc;
                        character.SendMessage(
                            "[QuestProbe] reportNpc expected={0} targetMatch={1}",
                            expectedNpc,
                            pass ? "PASS" : "FAIL");
                    }
                    character.SendMessage(
                        "[QuestProbe] act={0} type={1} detail={2}",
                        act.Id,
                        act.DetailType,
                        act.DetailId);
                }
            }

            character.SendMessage(
                "[QuestProbe] knownRequirements={0} unknownRequirements={1}",
                knownRequirementsPass ? "PASS" : "FAIL",
                unknownRequirements);
            Log.Info(
                "[QuestProbe] character={0} quest={1} active={2} completed={3} targetNpc={4} factionChain={5} knownReqs={6} unknownReqs={7}",
                character.Name,
                questId,
                character.Quests.HasQuest(questId),
                character.Quests.IsQuestComplete(questId),
                targetNpc?.TemplateId ?? 0,
                string.Join(">", factionChain),
                knownRequirementsPass,
                unknownRequirements);
        }

        public static void GetCommandChoice(Character character, string choice, string[] args)
        {
            uint questId;

            switch (choice)
            {
                case "diagnose":
                    if (args.Length >= 2 && uint.TryParse(args[1], out questId))
                        Diagnose(character, questId);
                    else
                        character.SendMessage("[QuestProbe] Usage: /quest diagnose <questId>");
                    break;
                case "try":
                    if (args.Length >= 2 && uint.TryParse(args[1], out questId))
                    {
                        Diagnose(character, questId);
                        character.Quests.Add(questId);
                        ReportQuestState(character, questId);
                    }
                    else
                        character.SendMessage("[QuestProbe] Usage: /quest try <questId>");
                    break;
                case "force":
                    if (args.Length >= 2 && uint.TryParse(args[1], out questId))
                    {
                        Diagnose(character, questId);
                        character.Quests.AddStart(questId);
                        character.Quests.Send();
                        character.Quests.SendCompleted();
                        ReportQuestState(character, questId);
                    }
                    else
                        character.SendMessage("[QuestProbe] Usage: /quest force <questId>");
                    break;
                case "sync":
                    character.Quests.Send();
                    character.Quests.SendCompleted();
                    character.SendMessage("[QuestProbe] active/completed snapshots sent");
                    break;
                case "add":
                    if (args.Length >= 2)
                    {
                        if (uint.TryParse(args[1], out questId))
                        {
                            character.Quests.AddStart(questId);
                        }
                    }
                    else
                    {
                        character.SendMessage("[Quest] Proper usage: /quest add <questId>\nBefore that, target the Npc you need for the quest");
                    }
                    break;
                case "list":
                    character.SendMessage("[Quest] LIST");
                    foreach (var quest in character.Quests.Quests.Values)
                    {
                        var objectives = quest.GetObjectives(quest.Step).Select(t => t.ToString()).ToList();
                        character.SendMessage("Quest {0}: Step({1}), Objectives({2})", quest.Template.Id, quest.Step, string.Join(", ", objectives));
                    }
                    break;
                case "reward":
                    if (args.Length >= 2)
                    {
                        if (uint.TryParse(args[1], out questId))
                        {
                            if (args.Length >= 3 && int.TryParse(args[2], out var selectedId))
                            {
                                character.Quests.Complete(questId, selectedId);
                            }
                            else
                            {
                                character.Quests.Complete(questId, 0);
                            }
                        }
                    }
                    else
                    {
                        character.SendMessage("[Quest] Proper usage: /quest reward <questId>");
                    }
                    break;
                case "step":
                    if (args.Length >= 2)
                    {
                        if (uint.TryParse(args[1], out questId))
                        {
                            if (character.Quests.HasQuest(questId))
                            {
                                if (args.Length >= 3 && uint.TryParse(args[2], out var stepId))
                                {
                                    if (character.Quests.SetStep(questId, stepId))
                                        character.SendMessage("[Quest] set Step {0} for Quest {1}", stepId, questId);
                                    else
                                        character.SendMessage("[Quest] Proper usage: /quest step <questId> <stepId>");
                                }
                            }
                            else
                            {
                                character.SendMessage("[Quest] You do not have the quest {0}", questId);
                            }
                        }
                    }
                    else
                    {
                        character.SendMessage("[Quest] Proper usage: /quest step <questId> <stepId>");
                    }
                    break;
                case "prog":
                    if (args.Length >= 2)
                    {
                        if (uint.TryParse(args[1], out questId))
                        {
                            if (character.Quests.HasQuest(questId))
                            {
                                var quest = character.Quests.Quests[questId];
                                if (quest.Step == QuestComponentKind.None)
                                    quest.Step = QuestComponentKind.Start;
                                if (quest.Step == QuestComponentKind.Start)
                                    quest.Step = QuestComponentKind.Supply;
                                else if (quest.Step == QuestComponentKind.Supply)
                                    quest.Step = QuestComponentKind.Progress;
                                else if (quest.Step == QuestComponentKind.Progress)
                                    quest.Step = QuestComponentKind.Ready;
                                else if (quest.Step == QuestComponentKind.Ready)
                                    quest.Step = QuestComponentKind.Reward;
                                else if (quest.Step > QuestComponentKind.Reward)
                                {
                                    quest.Drop(true);
                                    break;
                                }
                                character.SendMessage("[Quest] Perform step {1} for quest {0}", questId, quest.Step);
                                quest.Update();
                            }
                            else
                            {
                                character.SendMessage("[Quest] You do not have the quest {0}", questId);
                            }
                        }
                    }
                    else
                    {
                        character.SendMessage("[Quest] Proper usage: /quest update <questId>");
                    }
                    break;
                case "remove":
                    if (args.Length >= 2)
                    {
                        if (uint.TryParse(args[1], out questId))
                        {
                            if (character.Quests.HasQuest(questId))
                            {
                                character.Quests.Drop(questId, true);
                            }
                            else
                            {
                                character.SendMessage("[Quest] You do not have the quest {0}", questId);
                            }
                        }
                    }
                    else
                    {
                        character.SendMessage("[Quest] Proper usage: /quest remove <questId>");
                    }
                    break;
                default:
                    character.SendMessage("[Quest] /quest <diagnose/try/force/sync/add/remove/list/prog/reward>");
                    break;
            }
        }
    }
}
