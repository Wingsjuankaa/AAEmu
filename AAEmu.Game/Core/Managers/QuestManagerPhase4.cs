using AAEmu.Game.Models.Game.Quests.Acts;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Utils.DB;

using Microsoft.Data.Sqlite;

namespace AAEmu.Game.Core.Managers;

public partial class QuestManager
{
    public readonly record struct FamilyProgress(uint Level, uint Exp, uint Applied);

    private readonly List<(uint Level, ulong TotalExp, uint DailyExp)> _expeditionLevels = [];
    private readonly List<(uint Level, uint TotalExp)> _familyLevels = [];

    public (uint Level, uint DailyExp) GetExpeditionLevel(ulong totalExp)
    {
        var result = (Level: 1u, DailyExp: 0u);
        foreach (var level in _expeditionLevels)
        {
            if (level.TotalExp > totalExp)
                break;
            result = (level.Level, level.DailyExp);
        }
        return result;
    }

    public uint GetFamilyLevel(ulong totalExp)
    {
        return AdvanceFamilyProgress(1, 0, totalExp, _familyLevels).Level;
    }

    public FamilyProgress AdvanceFamilyProgress(uint level, uint exp, ulong requestedExp) =>
        AdvanceFamilyProgress(level, exp, requestedExp, _familyLevels);

    /// <summary>
    /// Advances AA10 family experience. Retail stores progress inside the current level;
    /// the next row's exp value is the amount required to cross into that level.
    /// </summary>
    public static FamilyProgress AdvanceFamilyProgress(uint level, uint exp, ulong requestedExp,
        IReadOnlyList<(uint Level, uint TotalExp)> levels)
    {
        if (levels.Count == 0 || requestedExp == 0)
            return new FamilyProgress(level, exp, 0);

        var ordered = levels.OrderBy(x => x.Level).ToArray();
        var currentLevel = Math.Max(level, ordered[0].Level);
        var currentExp = exp;
        ulong remaining = requestedExp;
        ulong applied = 0;

        while (remaining > 0)
        {
            var next = ordered.FirstOrDefault(x => x.Level > currentLevel);
            if (next == default)
                break; // Experience is capped at the retail maximum family level.

            var required = next.TotalExp;
            if (required == 0)
            {
                currentLevel = next.Level;
                currentExp = 0;
                continue;
            }

            if (currentExp >= required)
            {
                currentExp -= required;
                currentLevel = next.Level;
                continue;
            }

            var capacity = (ulong)required - currentExp;
            var step = Math.Min(capacity, remaining);
            currentExp += (uint)step;
            remaining -= step;
            applied += step;

            if (currentExp == required)
            {
                currentLevel = next.Level;
                currentExp = 0;
            }
        }

        return new FamilyProgress(currentLevel, currentExp, (uint)Math.Min(applied, uint.MaxValue));
    }

    private void LoadPhase4ProgressionLevels(SqliteConnection connection)
    {
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT id, total_exp, daily_exp FROM expedition_levels ORDER BY total_exp, id";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                _expeditionLevels.Add((reader.GetUInt32("id"), reader.GetUInt64("total_exp"), reader.GetUInt32("daily_exp")));
        }

        using (var command = connection.CreateCommand())
        {
            command.CommandText = "SELECT level, exp FROM family_levels ORDER BY exp, level";
            using var reader = new SQLiteWrapperReader(command.ExecuteReader());
            while (reader.Read())
                _familyLevels.Add((reader.GetUInt32("level"), reader.GetUInt32("exp")));
        }
    }

    private void LoadPhase4Rows(SqliteConnection connection, string table, string detailType,
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

    private void LoadPhase4QuestActTemplates(SqliteConnection connection)
    {
        LoadPhase4ProgressionLevels(connection);
        LoadPhase4Rows(connection, "quest_act_supply_actabilities", "QuestActSupplyActability", (parent, r) =>
            new QuestActSupplyActability(parent)
            {
                ActabilityGroupId = r.GetUInt32("actability_group_id"), Point = r.GetInt32("point")
            });
        LoadPhase4Rows(connection, "quest_act_supply_arche_pass_points", "QuestActSupplyArchePassPoint", (parent, r) =>
            new QuestActSupplyArchePassPoint(parent) { Point = r.GetInt32("point") });
        LoadPhase4Rows(connection, "quest_act_supply_contribution_points", "QuestActSupplyContributionPoint", (parent, r) =>
            new QuestActSupplyContributionPoint(parent) { Point = r.GetInt32("point") });
        LoadPhase4Rows(connection, "quest_act_supply_expedition_exps", "QuestActSupplyExpeditionExp", (parent, r) =>
            new QuestActSupplyExpeditionExp(parent) { Point = r.GetInt32("point") });
        LoadPhase4Rows(connection, "quest_act_supply_faction_changes", "QuestActSupplyFactionChange", (parent, r) =>
            new QuestActSupplyFactionChange(parent)
            {
                SystemFactionId = r.GetUInt32("system_faction_id"),
                IgnoreLimit = r.GetBoolean("ignore_limit", false),
                InferiorEscape = r.GetBoolean("inferior_escape", false)
            });
        LoadPhase4Rows(connection, "quest_act_supply_family_exps", "QuestActSupplyFamilyExp", (parent, r) =>
            new QuestActSupplyFamilyExp(parent) { Point = r.GetInt32("point") });
        LoadPhase4Rows(connection, "quest_act_supply_leadership_points", "QuestActSupplyLeadershipPoint", (parent, r) =>
            new QuestActSupplyLeadershipPoint(parent) { Point = r.GetInt32("point") });
        LoadPhase4Rows(connection, "quest_act_supply_local_lps", "QuestActSupplyLocalLp", (parent, r) =>
            new QuestActSupplyLocalLp(parent) { LocalLp = r.GetInt32("local_lp") });
        LoadPhase4Rows(connection, "quest_act_supply_ranked_items", "QuestActSupplyRankedItem", (parent, r) =>
            new QuestActSupplyRankedItem(parent)
            {
                Rank = r.GetInt32("rank"), ItemId = r.GetUInt32("item_id"),
                GradeId = r.GetByte("grade_id"), Count = r.GetInt32("count")
            });
        LoadPhase4Rows(connection, "quest_act_supply_resident_charges", "QuestActSupplyResidentCharge", (parent, r) =>
            new QuestActSupplyResidentCharge(parent)
            {
                ZoneGroupId = r.GetUInt32("zone_group_id"), Charge = r.GetInt32("charge")
            });
        LoadPhase4Rows(connection, "quest_act_supply_resident_points", "QuestActSupplyResidentPoint", (parent, r) =>
            new QuestActSupplyResidentPoint(parent)
            {
                ZoneGroupId = r.GetUInt32("zone_group_id"), Point = r.GetInt32("point")
            });
        LoadPhase4Rows(connection, "quest_act_supply_result_ranked_items", "QuestActSupplyResultRankedItem", (parent, r) =>
            new QuestActSupplyResultRankedItem(parent)
            {
                Result = r.GetBoolean("result", false), Rank = r.GetInt32("rank"),
                ItemId = r.GetUInt32("item_id"), GradeId = r.GetByte("grade_id"), Count = r.GetInt32("count")
            });
    }
}
