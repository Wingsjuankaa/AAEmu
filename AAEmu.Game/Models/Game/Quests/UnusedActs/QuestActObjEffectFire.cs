using AAEmu.Game.Models.Game.Quests.Templates;

#pragma warning disable IDE0130 // Namespace does not match folder structure

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// This Act does not seem to be used anymore
/// </summary>
public class QuestActObjEffectFire(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override AAEmu.Game.Models.Game.Units.QuestObjectiveEventType EventType => AAEmu.Game.Models.Game.Units.QuestObjectiveEventType.EffectFire;
    public uint EffectId { get; set; }
    public bool TeamShare { get; set; }

    protected override bool Matches(QuestAct questAct, AAEmu.Game.Models.Game.Units.OnQuestObjectiveArgs args)
    {
        var owner = questAct.QuestComponent.Parent.Parent.Owner;
        return args.EffectId == EffectId && (args.Actor?.Id == owner.Id || TeamShare);
    }
}
