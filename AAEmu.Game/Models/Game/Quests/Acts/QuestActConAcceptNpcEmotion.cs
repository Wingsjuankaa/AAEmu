using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConAcceptNpcEmotion(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public uint NpcId { get; set; }
    public string Emotion { get; set; }
    public uint EmotionId { get; set; }

    public static bool MatchesEmotionStart(
        QuestAcceptorType acceptorType,
        uint acceptorId,
        uint acceptorEmotionId,
        uint npcId,
        uint emotionId)
    {
        return acceptorType == QuestAcceptorType.Npc &&
               acceptorId == npcId &&
               npcId != 0 &&
               acceptorEmotionId == emotionId &&
               emotionId != 0;
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        Logger.Trace($"{QuestActTemplateName}({DetailId}).RunAct: Quest {quest.TemplateId}, Owner {quest.Owner.Name} ({quest.Owner.Id}), NpcId {NpcId}, Emotion {Emotion} ({EmotionId})");
        return MatchesEmotionStart(
            quest.QuestAcceptorType,
            quest.AcceptorId,
            quest.AcceptorEmotionId,
            NpcId,
            EmotionId);
    }
}
