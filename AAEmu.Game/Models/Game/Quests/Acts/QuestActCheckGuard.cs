using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActCheckGuard(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public uint NpcId { get; set; }

    public static bool IsLiveGuard(uint expectedNpcId, uint actualNpcId, bool isDead, int hp)
    {
        return expectedNpcId != 0 && actualNpcId == expectedNpcId && !isDead && hp > 0;
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        if (quest.Owner is not AAEmu.Game.Models.Game.Char.Character owner)
            return false;

        var live = owner.ParentWorld.GetAllNpcs()
            .Any(guard => IsLiveGuard(NpcId, guard.TemplateId, guard.IsDead, guard.Hp));
        Logger.Trace($"{QuestActTemplateName}({DetailId}).RunAct: Quest {quest.TemplateId}, Owner {quest.Owner.Name} ({quest.Owner.Id}), NpcId {NpcId}, Live {live}");
        return live;
    }
}
