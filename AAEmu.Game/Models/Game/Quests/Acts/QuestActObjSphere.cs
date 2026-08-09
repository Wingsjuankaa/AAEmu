using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActObjSphere : QuestActTemplate
    {
        public uint SphereId { get; set; }
        public uint NpcId { get; set; }
        public uint HighlightDoodadId { get; set; }
        public int HighlightDoodadPhase { get; set; }
        public bool UseAlias { get; set; }
        public uint QuestActObjAliasId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            _log.Debug(
                "QuestActObjSphere: Quest={0}, ComponentId={1}, Act={2}, objective={3}",
                quest.TemplateId,
                quest.ComponentId,
                Id,
                objective);
            return objective > 0;
        }
    }
}
