using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActCheckCompleteComponent : QuestActTemplate
    {
        public uint CompleteComponent { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            var complete = quest != null && quest.IsComponentComplete(CompleteComponent);
            _log.Debug(
                "QuestActCheckCompleteComponent: component={0}, complete={1}",
                CompleteComponent,
                complete);
            return complete;
        }
    }
}
