using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActConAcceptNpc : QuestActTemplate
    {
        public uint NpcId { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            _log.Debug("QuestActConAcceptNpc");

            var target = quest.InteractionTarget ?? character.CurrentTarget;
            if (!Quest.MatchesNpcTarget(target, NpcId))
            {
                _log.Warn(
                    "[AA8QuestTarget] AcceptNpc mismatch: quest={0}, npcTemplate={1}, " +
                    "explicitTarget={2}, currentTarget={3}",
                    quest.TemplateId,
                    NpcId,
                    quest.InteractionTarget?.GetType().Name ?? "null",
                    character.CurrentTarget?.GetType().Name ?? "null");
                return false;
            }

            quest.QuestAcceptorType = QuestAcceptorType.Npc;
            quest.AcceptorType = NpcId;

            return true;
        }
    }
}
