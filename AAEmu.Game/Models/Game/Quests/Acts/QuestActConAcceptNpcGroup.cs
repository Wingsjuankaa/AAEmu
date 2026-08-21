using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts;

public class QuestActConAcceptNpcGroup(QuestComponentTemplate parentComponent) : QuestActTemplate(parentComponent)
{
    public uint QuestMonsterGroupId { get; set; }

    public static bool MatchesAcceptor(
        QuestAcceptorType acceptorType,
        uint acceptorId,
        uint groupId,
        Func<uint, uint, bool> groupContainsNpc)
    {
        return acceptorType == QuestAcceptorType.Npc &&
               acceptorId != 0 &&
               groupId != 0 &&
               groupContainsNpc(groupId, acceptorId);
    }

    public override bool RunAct(Quest quest, QuestAct questAct, int currentObjectiveCount)
    {
        Logger.Trace($"{QuestActTemplateName}({DetailId}).RunAct: Quest {quest.TemplateId}, Owner {quest.Owner.Name} ({quest.Owner.Id}), Group {QuestMonsterGroupId}, Acceptor {quest.AcceptorId}");
        return MatchesAcceptor(
            quest.QuestAcceptorType,
            quest.AcceptorId,
            QuestMonsterGroupId,
            QuestManager.Instance.CheckGroupNpc);
    }
}
