using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Utils.DB;

using MySql.Data.MySqlClient;

using NLog;

namespace AAEmu.Game.Models.Game.Char
{
    public class CharacterQuests
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();
        private readonly List<uint> _removed;

        public Character Owner { get; set; }

        public Dictionary<uint, Quest> Quests { get; }
        public Dictionary<ushort, CompletedQuest> CompletedQuests { get; }

        public CharacterQuests(Character owner)
        {
            Owner = owner;
            Quests = new Dictionary<uint, Quest>();
            CompletedQuests = new Dictionary<ushort, CompletedQuest>();
            _removed = new List<uint>();
        }

        public bool HasQuest(uint questId)
        {
            return Quests.ContainsKey(questId);
        }

        public bool CanAcquireQuestLoot(
            uint questId,
            uint itemId,
            int amount)
        {
            if (!HasExactItemGatherRelation(questId, itemId))
                return true;

            return Quests.TryGetValue(questId, out var quest) &&
                   quest.NeedsItemGather(itemId, amount);
        }

        private static bool HasExactItemGatherRelation(
            uint questId,
            uint itemId)
        {
            var template = QuestManager.Instance.GetTemplate(questId);
            if (template == null)
                return false;

            foreach (var component in template.GetComponents(
                         QuestComponentKind.Progress))
            {
                foreach (var act in QuestManager.Instance.GetActs(component.Id))
                {
                    if (act.DetailType != nameof(QuestActObjItemGather))
                        continue;

                    var gather = act.GetTemplate<QuestActObjItemGather>();
                    if (gather?.ItemId == itemId)
                        return true;
                }
            }

            return false;
        }

        /// <summary>
        /// Resolves a character-local doodad phase declared by an active quest
        /// interaction objective. Doodads marked once_one_man must not move
        /// their shared world phase when only one character advances a quest.
        /// </summary>
        public bool TryGetInteractionDoodadPhase(uint doodadTemplateId, out uint phase)
        {
            phase = 0;
            foreach (var quest in Quests.Values)
            {
                if (quest.Status != QuestStatus.Progress)
                    continue;

                foreach (var component in quest.Template.GetComponents(QuestComponentKind.Progress))
                {
                    foreach (var act in QuestManager.Instance.GetActs(component.Id))
                    {
                        if (act.DetailType != nameof(QuestActObjInteraction))
                            continue;

                        var interaction = act.GetTemplate<QuestActObjInteraction>();
                        if (interaction == null || interaction.HighlightDoodadPhase <= 0)
                            continue;
                        if (interaction.DoodadId != doodadTemplateId &&
                            interaction.HighlightDoodadId != doodadTemplateId)
                            continue;

                        phase = (uint)interaction.HighlightDoodadPhase;
                        return true;
                    }
                }
            }

            return false;
        }

        public void Add(uint questId, BaseUnit interactionTarget = null)
        {
            if (Quests.ContainsKey(questId))
            {
                _log.Warn("Duplicate quest {0}, not added!", questId);
                return;
            }

            var template = QuestManager.Instance.GetTemplate(questId);
            if (template == null)
                return;
            if (!QuestStartDependencyGuard.CanStart(
                    template,
                    out var unavailableItemId,
                    out var dependencyReason))
            {
                _log.Warn(
                    "[AA8QuestStartGuard] Rejected quest {0} for {1}: " +
                    "unavailable initial supply item {2}, reason={3}",
                    questId,
                    Owner.Name,
                    unavailableItemId,
                    dependencyReason);
                Owner.SendMessage(
                    "[Quest] Quest {0} is temporarily unavailable because " +
                    "an initial item dependency is incomplete.",
                    questId);
                return;
            }
            var quest = new Quest(template);
            quest.Id = QuestIdManager.Instance.GetNextId();
            quest.Status = QuestStatus.Progress;
            quest.Owner = Owner;
            Quests.Add(quest.TemplateId, quest);

            if (QuestManager.Instance.QuestTimeoutTask.Count != 0)
            {
                if (QuestManager.Instance.QuestTimeoutTask.ContainsKey(quest.Owner.Id) && QuestManager.Instance.QuestTimeoutTask[quest.Owner.Id].ContainsKey(questId))
                    QuestManager.Instance.QuestTimeoutTask[quest.Owner.Id].Remove(questId);
            }

            quest.InteractionTarget = interactionTarget;
            bool res;
            try
            {
                res = quest.Start();
            }
            finally
            {
                quest.InteractionTarget = null;
            }
            if (!res)
                Drop(questId, true); // TODO может быть update = false?
            //else
            //    Owner.SendPacket(new SCQuestContextStartedPacket(quest, res));
            quest.Owner.SendMessage("[Quest] {0}, quest {1} added.", Owner.Name, questId);
        }

        /// <summary>
        /// Метод предназначен для вызова из скрита QuestCmd, команда /quest add <questId>
        /// </summary>
        /// <param name="questId"></param>
        public void AddStart(uint questId)
        {
            if (Quests.ContainsKey(questId))
            {
                _log.Warn("Duplicate quest {0}, added!", questId);
                Drop(questId, true);
            }

            var template = QuestManager.Instance.GetTemplate(questId);
            if (template == null)
                return;
            var quest = new Quest(template);
            quest.Id = QuestIdManager.Instance.GetNextId();
            quest.Status = QuestStatus.Progress;
            quest.Owner = Owner;
            Quests.Add(quest.TemplateId, quest);

            quest.StartFirstOnly();
            quest.Owner.SendMessage("[Quest] {0}, quest {1} added.", Owner.Name, questId);
        }

        public void Complete(
            uint questId,
            int selected,
            bool supply = true,
            BaseUnit interactionTarget = null)
        {
            if (!Quests.ContainsKey(questId))
            {
                _log.Warn("Complete not exist quest {0}", questId);
                return;
            }

            var quest = Quests[questId];
            if (quest.IsCompleting)
            {
                _log.Warn(
                    "[AA8QuestCompletionGuard] Reentrant completion blocked: character={0}, quest={1}",
                    Owner.Name, questId);
                return;
            }

            quest.IsCompleting = true;
            quest.InteractionTarget = interactionTarget;
            try
            {
                var res = quest.Complete(selected);
                if (res != 0)
                {
                    if (supply)
                    {
                        var exps = quest.GetCustomExp();
                        var amount = quest.GetCustomCopper();
                        var supplies = QuestManager.Instance.GetSupplies(quest.Template.Level);
                        if (supplies != null)
                        {
                            if (quest.Template.LetItDone)
                            {
                                // Добавим|убавим за перевыполнение|недовыполнение плана, если позволено квестом
                                if (exps == 0)
                                    Owner.AddExp(supplies.Exp * quest.OverCompletionPercent / 100, true);
                                if (amount == 0)
                                    amount = supplies.Copper * quest.OverCompletionPercent / 100;
                                Owner.Money += amount;

                                if (!quest.ExtraCompletion)
                                {
                                    // посылаем пакет, так как он был пропущен в методе Update()
                                    quest.Status = QuestStatus.Progress;
                                    Owner.SendPacket(new SCQuestContextUpdatedPacket(quest, quest.ComponentId));
                                    quest.Status = QuestStatus.Completed;
                                }
                            }
                            else
                            {
                                if (exps == 0)
                                    Owner.AddExp(supplies.Exp, true);
                                if (amount == 0)
                                    amount = supplies.Copper;
                                Owner.Money += amount;
                            }

                            Owner.SendPacket(
                                new SCItemTaskSuccessPacket(
                                    ItemTaskType.QuestComplete,
                                    new List<ItemTask>
                                    {
                                        new MoneyChange(amount)
                                    },
                                    new List<ulong>())
                            );
                        }
                    }
                    var completeId = (ushort)(quest.TemplateId / 64);
                    if (!CompletedQuests.ContainsKey(completeId))
                        CompletedQuests.Add(completeId, new CompletedQuest(completeId));
                    var complete = CompletedQuests[completeId];
                    complete.Body.Set((int)(quest.TemplateId - completeId * 64), true);
                    var body = new byte[8];
                    complete.Body.CopyTo(body, 0);
                    Drop(questId, false);
                    //OnQuestComplete(questId);
                    Owner.SendPacket(new SCQuestContextCompletedPacket(quest.TemplateId, body, res));
                }
            }
            finally
            {
                quest.InteractionTarget = null;
                quest.IsCompleting = false;
            }
        }

        public void Drop(uint questId, bool update)
        {
            if (!Quests.ContainsKey(questId))
                return;
            var quest = Quests[questId];
            quest.Drop(update);
            Quests.Remove(questId);
            _removed.Add(questId);

            quest.Owner.SendMessage("[Quest] {0}, quest {1} removed.", Owner.Name, questId);
            _log.Warn("[Quest] {0}, quest {1} removed.", Owner.Name, questId);

            if (QuestManager.Instance.QuestTimeoutTask.ContainsKey(quest.Owner.Id))
            {
                if (QuestManager.Instance.QuestTimeoutTask[quest.Owner.Id].ContainsKey(questId))
                {
                    _ = QuestManager.Instance.QuestTimeoutTask[quest.Owner.Id][questId].Cancel();
                    _ = QuestManager.Instance.QuestTimeoutTask[quest.Owner.Id].Remove(questId);
                }
            }

            QuestIdManager.Instance.ReleaseId((uint)quest.Id);
        }

        public bool SetStep(uint questContextId, uint step)
        {
            if (step > 8)
                return false;

            if (!Quests.ContainsKey(questContextId))
                return false;

            var quest = Quests[questContextId];
            quest.Step = (QuestComponentKind)step;
            return true;
        }

        public void OnReportToNpc(uint objId, uint questId, int selected)
        {
            if (!Quests.ContainsKey(questId))
                return;

            var quest = Quests[questId];

            var npc = WorldManager.Instance.GetNpc(objId);
            if (npc == null)
                return;

            //if (npc.GetDistanceTo(Owner) > 8.0f)
            //    return;

            if (!quest.CanReportToNpc(npc))
            {
                _log.Warn(
                    "[AA8QuestNpc] Invalid report target/state: character={0}, quest={1}, " +
                    "status={2}, npcTemplate={3}, objId={4}",
                    Owner.Name, questId, quest.Status, npc.TemplateId, npc.ObjId);
                return;
            }

            Complete(questId, selected, true, npc);
        }

        public void OnReportToDoodad(uint objId, uint questId, int selected)
        {
            if (!Quests.ContainsKey(questId))
                return;

            var quest = Quests[questId];

            var doodad = WorldManager.Instance.GetDoodad(objId);
            if (doodad == null)
                return;

            // if (npc.GetDistanceTo(Owner) > 8.0f)
            //     return;

            if (!quest.CanReportToDoodad(doodad))
            {
                _log.Warn(
                    "[AA8QuestDoodad] Invalid report target/state: character={0}, quest={1}, " +
                    "status={2}, doodadTemplate={3}, objId={4}",
                    Owner.Name, questId, quest.Status, doodad.TemplateId, doodad.ObjId);
                return;
            }

            _log.Info(
                "[AA8QuestDoodad] Completing validated report: character={0}, quest={1}, " +
                "doodadTemplate={2}, objId={3}, selected={4}",
                Owner.Name, questId, doodad.TemplateId, doodad.ObjId, selected);
            Complete(questId, selected, true, doodad);
        }

        public void OnTalkMade(uint npcObjId, uint questContextId, uint questComponentId, uint questActId)
        {
            var npc = WorldManager.Instance.GetNpc(npcObjId);
            if (npc == null)
                return;

            if (Owner.CurrentTarget == null || Owner.CurrentTarget.ObjId != npcObjId)
                return;

            if (npc.GetDistanceTo(Owner) > 8.0f)
                return;

            if (!Quests.ContainsKey(questContextId))
                return;

            var quest = Quests[questContextId];
            if (!quest.OnTalkMade(
                    npc,
                    questContextId,
                    questComponentId,
                    questActId))
            {
                _log.Warn(
                    "[AA8QuestTalk] Rejected talk event: character={0}, npcObjId={1}, " +
                    "npcTemplate={2}, quest={3}, component={4}, act={5}, status={6}, step={7}",
                    Owner.Name,
                    npcObjId,
                    npc.TemplateId,
                    questContextId,
                    questComponentId,
                    questActId,
                    quest.Status,
                    quest.Step);
            }
        }

        public void OnKill(Npc npc)
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnKill(npc);
        }

        /// <summary>
        /// Взаимодействие с doodad, например сбор ресурсов
        /// </summary>
        /// <param name="item"></param>
        /// <param name="count"></param>
        public void OnItemGather(Item item, int count)
        {
            //if (!Quests.ContainsKey(item.Template.LootQuestId))
            //    return;
            //var quest = Quests[item.Template.LootQuestId];
            foreach (var quest in Quests.Values.ToList())
                quest.OnItemGather(item, count);
        }

        /// <summary>
        /// Использование предмета в инвентаре
        /// </summary>
        /// <param name="item"></param>
        public void OnItemUse(Item item)
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnItemUse(item);
        }

        /// <summary>
        /// Взаимодействие с doodad, например ломаем шахту по квесту
        /// </summary>
        /// <param name="type"></param>
        /// <param name="target"></param>
        public void OnInteraction(WorldInteractionType type, Units.BaseUnit target)
        {
            foreach (var quest in Quests.Values)
                quest.OnInteraction(type, target);
        }

        public void OnLevelUp()
        {
            foreach (var quest in Quests.Values)
                quest.OnLevelUp();
        }

        public void OnQuestComplete(uint questId)
        {
            foreach (var quest in Quests.Values)
                quest.OnQuestComplete(questId);
        }

        public void OnEnterSphere(SphereQuest sphereQuest)
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnEnterSphere(sphereQuest);
        }

        public void OnCinemaCompleted()
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnCinemaCompleted();
        }

        public void OnEffectFire(uint effectId)
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnEffectFire(effectId);
        }

        public void OnDoodadPhaseChanged(Doodad doodad)
        {
            foreach (var quest in Quests.Values.ToList())
                quest.OnDoodadPhaseChanged(doodad);
        }

        public void AddCompletedQuest(CompletedQuest quest)
        {
            CompletedQuests.Add(quest.Id, quest);
        }

        public CompletedQuest GetCompletedQuest(ushort id)
        {
            return CompletedQuests.ContainsKey(id) ? CompletedQuests[id] : null;
        }

        public bool IsQuestComplete(uint questId)
        {
            var completeId = (ushort)(questId / 64);
            if (!CompletedQuests.ContainsKey(completeId))
                return false;
            return CompletedQuests[completeId].Body[(int)(questId - completeId * 64)];
        }

        public void Send()
        {
            var quests = Quests.Values.ToArray();
            if (quests.Length <= 20)
            {
                Owner.SendPacket(new SCQuestsPacket(quests));
            }
            else
            {
                for (var i = 0; i < quests.Length; i += 20)
                {
                    var size = quests.Length - i >= 20 ? 20 : quests.Length - i;
                    var res = new Quest[size];
                    Array.Copy(quests, i, res, 0, size);
                    Owner.SendPacket(new SCQuestsPacket(res));
                }
            }

        }

        public void SendCompleted()
        {
            var completedQuests = CompletedQuests.Values.ToArray();
            if (completedQuests.Length <= 200)
            {
                Owner.SendPacket(new SCCompletedQuestsPacket(completedQuests));
                return;
            }

            for (var i = 0; i < completedQuests.Length; i += 20)
            {
                var size = completedQuests.Length - i >= 200 ? 200 : completedQuests.Length - i;
                var result = new CompletedQuest[size];
                Array.Copy(completedQuests, i, result, 0, size);
                Owner.SendPacket(new SCCompletedQuestsPacket(result));
            }
        }

        public void Load(MySqlConnection connection)
        {
            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM completed_quests WHERE `owner` = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var quest = new CompletedQuest();
                        quest.Id = reader.GetUInt16("id");
                        quest.Body = new BitArray((byte[])reader.GetValue("data"));
                        CompletedQuests.Add(quest.Id, quest);
                    }
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.CommandText = "SELECT * FROM quests WHERE `owner` = @owner";
                command.Parameters.AddWithValue("@owner", Owner.Id);
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        var quest = new Quest();
                        quest.Id = reader.GetUInt32("id");
                        quest.TemplateId = reader.GetUInt32("template_id");
                        quest.Status = (QuestStatus)reader.GetByte("status");
                        quest.ReadData((byte[])reader.GetValue("data"));
                        quest.Owner = Owner;
                        quest.Template = QuestManager.Instance.GetTemplate(quest.TemplateId);
                        if (quest.NormalizePersistedReadyBoundary())
                        {
                            _log.Warn(
                                "[Quest] Repaired persisted Ready boundary for quest {0} on {1}: Step={2}, ComponentId={3}",
                                quest.TemplateId,
                                Owner.Name,
                                quest.Step,
                                quest.ComponentId);
                        }
                        else if (quest.NormalizeImmediateReadyStep())
                        {
                            _log.Info(
                                "[Quest] Normalized immediate-ready quest {0} for {1}: Step={2}, ComponentId={3}",
                                quest.TemplateId,
                                Owner.Name,
                                quest.Step,
                                quest.ComponentId);
                        }
                        quest.RecalcObjectives(false);
                        Quests.Add(quest.TemplateId, quest);
                    }
                }
            }

            // Quest.Time is already part of the persisted quest blob. Re-arm
            // native timers after every active quest has been materialized so
            // an expired deadline reaches the ordinary failure/drop path
            // instead of being silently reset by a relog.
            foreach (var quest in Quests.Values)
                QuestManager.Instance.RestoreQuestTimeout(Owner, quest);
        }

        public void Save(MySqlConnection connection, MySqlTransaction transaction)
        {
            if (_removed.Count > 0)
            {
                using (var command = connection.CreateCommand())
                {
                    command.Connection = connection;
                    command.Transaction = transaction;

                    var ids = string.Join(",", _removed);
                    command.CommandText = $"DELETE FROM quests WHERE owner = @owner AND template_id IN({ids})";
                    command.Prepare();
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();
                }

                _removed.Clear();
            }

            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText = "REPLACE INTO completed_quests(`id`,`data`,`owner`) VALUES(@id,@data,@owner)";
                foreach (var quest in CompletedQuests.Values)
                {
                    command.Parameters.AddWithValue("@id", quest.Id);
                    var body = new byte[8];
                    quest.Body.CopyTo(body, 0);
                    command.Parameters.AddWithValue("@data", body);
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();

                    command.Parameters.Clear();
                }
            }

            using (var command = connection.CreateCommand())
            {
                command.Connection = connection;
                command.Transaction = transaction;

                command.CommandText =
                    "REPLACE INTO quests(`id`,`template_id`,`data`,`status`,`owner`) VALUES(@id,@template_id,@data,@status,@owner)";

                foreach (var quest in Quests.Values)
                {
                    command.Parameters.AddWithValue("@id", quest.Id);
                    command.Parameters.AddWithValue("@template_id", quest.TemplateId);
                    command.Parameters.AddWithValue("@data", quest.WriteData());
                    command.Parameters.AddWithValue("@status", (byte)quest.Status);
                    command.Parameters.AddWithValue("@owner", Owner.Id);
                    command.ExecuteNonQuery();

                    command.Parameters.Clear();
                }
            }
        }
    }
}
