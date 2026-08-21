using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

namespace AAEmu.Game.Core.Managers;

public partial class QuestManager
{
    private readonly Dictionary<uint, List<uint>> _groupQuests = [];

    public IReadOnlyList<uint> GetGroupQuests(uint groupId) =>
        _groupQuests.TryGetValue(groupId, out var quests) ? quests : [];

    public bool CheckGroupQuest(uint groupId, uint questId) =>
        _groupQuests.TryGetValue(groupId, out var quests) && quests.Contains(questId);

    private void LoadQuestContextGroups(SqliteConnection connection)
    {
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT quest_context_group_id, context_id FROM quest_context_group_members ORDER BY quest_context_group_id, context_id";
        command.Prepare();
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
        {
            var groupId = reader.GetUInt32("quest_context_group_id");
            if (!_groupQuests.TryGetValue(groupId, out var quests))
            {
                quests = [];
                _groupQuests.Add(groupId, quests);
            }
            quests.Add(reader.GetUInt32("context_id"));
        }
    }

    private void LoadPhase3Rows(SqliteConnection connection, string table, string detailType,
        Func<QuestComponentTemplate, SQLiteWrapperReader, QuestActTemplate> factory)
    {
        using var command = connection.CreateCommand();
        command.CommandText = $"SELECT * FROM {table}";
        command.Prepare();
        using var reader = new SQLiteWrapperReader(command.ExecuteReader());
        while (reader.Read())
        {
            var id = reader.GetUInt32("id");
            var parent = GetComponentByActTemplate(detailType, id);
            if (parent == null)
                continue;
            var template = factory(parent, reader);
            template.DetailId = id;
            AddActTemplate(template);
        }
    }

    private static void ReadAlias(SQLiteWrapperReader reader, QuestActObjPhase3Event template)
    {
        template.UseAlias = reader.GetBoolean("use_alias", true);
        template.QuestActObjAliasId = reader.GetUInt32("quest_act_obj_alias_id", 0);
    }

    internal static T ReadPointObjective<T>(SQLiteWrapperReader reader, T template)
        where T : QuestActObjPhase3Event
    {
        // The three AA10 gain-point tables contain only id + point. Alias fields
        // exist on the shared runtime type but are not authored for these rows.
        template.Count = reader.GetInt32("point");
        return template;
    }

    private void LoadPhase3QuestActTemplates(SqliteConnection connection)
    {
        LoadPhase3Rows(connection, "quest_act_obj_complete_quest_groups", "QuestActObjCompleteQuestGroup", (parent, r) =>
            new QuestActObjCompleteQuestGroup(parent)
            {
                QuestContextGroupId = r.GetUInt32("quest_context_group_id"),
                AcceptWith = r.GetBoolean("accept_with", false),
                UseAlias = r.GetBoolean("use_alias", true),
                QuestActObjAliasId = r.GetUInt32("quest_act_obj_alias_id", 0),
                Count = r.GetInt32("count", 1)
            });

        LoadPhase3Rows(connection, "quest_act_obj_conquest_wars", "QuestActObjConquestWar", (parent, r) =>
        {
            var template = new QuestActObjConquestWar(parent)
            {
                ZoneGroupId = r.GetUInt32("zone_group_id"), CompleteRank = r.GetInt32("complete_rank"), Count = 1
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_consume_evolving_materials", "QuestActObjConsumeEvolvingMaterial", (parent, r) =>
        {
            var template = new QuestActObjConsumeEvolvingMaterial(parent) { Count = r.GetInt32("count") };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_enchant_scale_counts", "QuestActObjEnchantScaleCount", (parent, r) =>
        {
            var template = new QuestActObjEnchantScaleCount(parent) { Count = r.GetInt32("count") };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_faction_competitions", "QuestActObjFactionCompetition", (parent, r) =>
        {
            var template = new QuestActObjFactionCompetition(parent)
            {
                ZoneGroupId = r.GetUInt32("zone_group_id"), CompleteRank = r.GetInt32("complete_rank"),
                UseResult = r.GetBoolean("use_result", false), Count = 1
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_gain_exp_points", "QuestActObjGainExpPoint", (parent, r) =>
            ReadPointObjective(r, new QuestActObjGainExpPoint(parent)));
        LoadPhase3Rows(connection, "quest_act_obj_gain_honor_points", "QuestActObjGainHonorPoint", (parent, r) =>
            ReadPointObjective(r, new QuestActObjGainHonorPoint(parent)));
        LoadPhase3Rows(connection, "quest_act_obj_gain_living_points", "QuestActObjGainLivingPoint", (parent, r) =>
            ReadPointObjective(r, new QuestActObjGainLivingPoint(parent)));

        LoadPhase3Rows(connection, "quest_act_obj_invite_team_factions", "QuestActObjInviteTeamFaction", (parent, r) =>
        {
            var template = new QuestActObjInviteTeamFaction(parent)
            {
                QuestActObjInviteId = r.GetUInt32("quest_act_obj_invite_id"), BuffId = r.GetUInt32("buff_id"), Count = r.GetInt32("count")
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_monster_contr_hunts", "QuestActObjMonsterContrHunt", (parent, r) =>
        {
            var template = new QuestActObjMonsterContrHunt(parent)
            {
                NpcId = r.GetUInt32("npc_id"), Count = r.GetInt32("count"),
                HighlightDoodadId = r.GetUInt32("highlight_doodad_id", 0),
                HighlightDoodadPhase = r.GetInt32("highlight_doodad_phase", -1), LongDist = r.GetBoolean("long_dist", false)
            };
            ReadAlias(r, template);
            return template;
        });
        LoadPhase3Rows(connection, "quest_act_obj_monster_contr_group_hunts", "QuestActObjMonsterContrGroupHunt", (parent, r) =>
        {
            var template = new QuestActObjMonsterContrGroupHunt(parent)
            {
                QuestMonsterGroupId = r.GetUInt32("quest_monster_group_id"), Count = r.GetInt32("count"),
                HighlightDoodadId = r.GetUInt32("highlight_doodad_id", 0),
                HighlightDoodadPhase = r.GetInt32("highlight_doodad_phase", -1), LongDist = r.GetBoolean("long_dist", false)
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_npc_kills", "QuestActObjNpcKill", (parent, r) =>
        {
            var template = new QuestActObjNpcKill(parent)
            {
                LevelMin = r.GetInt32("level_min"), LevelMax = r.GetInt32("level_max"),
                HeirLevelMin = r.GetInt32("heir_level_min"), HeirLevelMax = r.GetInt32("heir_level_max"),
                GradeBitFlag = r.GetInt32("grade_bit_flag"), Count = r.GetInt32("count"),
                LongDist = r.GetBoolean("long_dist", false), TeamShare = r.GetBoolean("team_share", false),
                IsParty = r.GetBoolean("is_party", false)
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_pc_kills", "QuestActObjPcKill", (parent, r) =>
        {
            var template = new QuestActObjPcKill(parent)
            {
                LevelGap = r.GetInt32("level_gap"), Count = r.GetInt32("count"),
                TeamShare = r.GetBoolean("team_share", false), IsParty = r.GetBoolean("is_party", false)
            };
            ReadAlias(r, template);
            return template;
        });

        LoadPhase3Rows(connection, "quest_act_obj_sell_backpack_goods", "QuestActObjSellBackpackGood", (parent, r) =>
        {
            var template = new QuestActObjSellBackpackGood(parent)
            {
                ContentItemId = r.GetUInt32("content_item_id"), ContentItemType = r.GetString("content_item_type", string.Empty),
                Count = r.GetInt32("count"), QuestMonsterGroupId = r.GetUInt32("quest_monster_group_id", 0)
            };
            ReadAlias(r, template);
            return template;
        });
    }
}
