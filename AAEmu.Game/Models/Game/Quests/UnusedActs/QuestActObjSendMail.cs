using AAEmu.Game.Models.Game.Quests.Templates;

#pragma warning disable IDE0130 // Namespace does not match folder structure

namespace AAEmu.Game.Models.Game.Quests.Acts;

/// <summary>
/// Not used
/// </summary>
/// <param name="parentComponent"></param>
public class QuestActObjSendMail(QuestComponentTemplate parentComponent) : QuestActObjPhase3Event(parentComponent)
{
    protected override AAEmu.Game.Models.Game.Units.QuestObjectiveEventType EventType => AAEmu.Game.Models.Game.Units.QuestObjectiveEventType.SendMail;
    public uint ItemId1 { get; set; }
    public int Count1 { get; set; }
    public uint ItemId2 { get; set; }
    public int Count2 { get; set; }
    public uint ItemId3 { get; set; }
    public int Count3 { get; set; }

    public static bool ContainsRequirements(IReadOnlyDictionary<uint, int> items, params (uint Id, int Count)[] requirements) =>
        requirements.Where(x => x.Id > 0 && x.Count > 0)
            .All(x => items != null && items.TryGetValue(x.Id, out var count) && count >= x.Count);

    protected override bool Matches(QuestAct questAct, AAEmu.Game.Models.Game.Units.OnQuestObjectiveArgs args) =>
        base.Matches(questAct, args) && ContainsRequirements(args.Items,
            (ItemId1, Count1), (ItemId2, Count2), (ItemId3, Count3));
}
