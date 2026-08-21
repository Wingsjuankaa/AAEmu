using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConAcceptLevelRange(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public byte LevelMin { get; set; }
    public byte LevelMax { get; set; }

    public static bool ContainsLevel(byte level, byte levelMin, byte levelMax)
    {
        return levelMin <= levelMax && level >= levelMin && level <= levelMax;
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        Logger.Trace($"{QuestActTemplateName}({DetailId}).RunAct: Quest {quest.TemplateId}, Owner {quest.Owner.Name} ({quest.Owner.Id}), Level {quest.Owner.Level}, Range {LevelMin}-{LevelMax}");
        return ContainsLevel(quest.Owner.Level, LevelMin, LevelMax);
    }
}
