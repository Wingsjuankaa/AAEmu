using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs
{
    public class DoodadFuncQuest : DoodadFuncTemplate
    {
        // doodad_funcs
        public uint QuestKindId { get; set; }
        public uint QuestId { get; set; }

        public override void Use(Unit caster, Doodad owner, uint skillId, int nextPhase = 0)
        {
            if (!(caster is Character character))
                return;

            _log.Info(
                "[AA8QuestDoodad] Execute: character={0}, doodadTemplate={1}, objId={2}, " +
                "questKind={3}, quest={4}, skill={5}",
                character.Name, owner.TemplateId, owner.ObjId, QuestKindId, QuestId, skillId);

            switch (QuestKindId)
            {
                case 1 when !character.Quests.HasQuest(QuestId):
                    character.Quests.Add(QuestId, owner);
                    break;
                case 2 when character.Quests.HasQuest(QuestId):
                    character.Quests.OnReportToDoodad(owner.ObjId, QuestId, 0);
                    break;
                default:
                    _log.Warn(
                        "[AA8QuestDoodad] Rejected state: character={0}, doodadTemplate={1}, " +
                        "questKind={2}, quest={3}, active={4}, completed={5}",
                        character.Name, owner.TemplateId, QuestKindId, QuestId,
                        character.Quests.HasQuest(QuestId),
                        character.Quests.IsQuestComplete(QuestId));
                    break;
            }
        }
    }
}
