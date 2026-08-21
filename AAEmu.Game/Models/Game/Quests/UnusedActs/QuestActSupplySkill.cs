using AAEmu.Game.Models.Game.Quests.Templates;

#pragma warning disable IDE0130 // Namespace does not match folder structure

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Skills.Static;

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// Executes the authored hidden quest skill on the quest owner.
/// AA10 retail uses this for immediate effects (for example permanent
/// actability gain and a notification buff), not for learning a player skill.
/// </summary>
/// <param name="parentComponent"></param>
public class QuestActSupplySkill(QuestComponentTemplate parentComponent) : QuestActSupplyPhase4(parentComponent)
{
    public uint SkillId { get; set; }

    protected override bool CanApplyCore(Quest quest, QuestAct questAct) =>
        quest?.Owner != null && SkillId != 0 && SkillManager.Instance.GetSkillTemplate(SkillId) != null;

    protected override bool ApplyReward(Quest quest, QuestAct questAct) =>
        IsSuccessful(quest.Owner.UseSkill(SkillId, quest.Owner));

    internal static bool IsSuccessful(SkillResult result) => result == SkillResult.Success;
}
