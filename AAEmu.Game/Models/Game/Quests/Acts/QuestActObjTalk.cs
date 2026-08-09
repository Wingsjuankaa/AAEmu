using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActObjTalk : QuestActTemplate
    {
        public uint NpcId { get; set; }
        public bool TeamShare { get; set; }
        public uint ItemId { get; set; }
        public bool UseAlias { get; set; }
        public uint QuestActObjAliasId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            // OnTalkMade validates the explicit NPC object before incrementing
            // this objective. Do not re-read mutable Character.CurrentTarget
            // while Update evaluates the already validated event.
            _log.Debug("QuestActObjTalk: NpcId {0}, objective {1}", NpcId, objective);
            return objective > 0;
        }
    }
}
