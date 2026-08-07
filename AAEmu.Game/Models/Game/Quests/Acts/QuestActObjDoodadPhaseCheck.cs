using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActObjDoodadPhaseCheck : QuestActTemplate
    {
        public uint DoodadId { get; set; }
        public uint Phase1 { get; set; }
        public uint Phase2 { get; set; }
        public bool UseAlias { get; set; }
        public uint QuestActObjAliasId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            _log.Debug(
                "QuestActObjDoodadPhaseCheck: DoodadId {0}, Phase1 {1}, Phase2 {2}, objective {3}",
                DoodadId,
                Phase1,
                Phase2,
                objective);
            return objective > 0;
        }
    }
}
