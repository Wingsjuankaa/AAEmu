using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

public class DoodadFuncQuest : DoodadFuncTemplate
{
    public const uint OfferQuestKind = 1;
    public const uint ReportQuestKind = 2;

    // doodad_funcs
    public uint QuestKindId { get; set; }
    public uint QuestId { get; set; }

    public static bool IsEligible(uint questKindId, bool isActive, bool isComplete, bool repeatable)
    {
        return questKindId switch
        {
            OfferQuestKind => !isActive && (!isComplete || repeatable),
            ReportQuestKind => isActive,
            _ => false
        };
    }

    /// <summary>
    /// Offers must satisfy the same context and Start component gates as AddQuest, before
    /// opening the client's quest camera. Reports do not re-evaluate acceptance gates.
    /// </summary>
    public static bool IsEligible(uint questKindId, Character character, QuestTemplate template)
    {
        if (character == null || template == null ||
            !IsEligible(questKindId, character.Quests.HasQuest(template.Id),
                character.Quests.IsQuestComplete(template.Id), template.Repeatable))
            return false;

        return questKindId != OfferQuestKind ||
               template.MeetsContextRequirements(character) &&
               template.GetComponents(QuestComponentKind.Start)
                   .All(component => UnitRequirementsGameData.Instance.CanComponentRun(component, character));
    }

    public override void Use(BaseUnit caster, Doodad owner, uint skillId, int nextPhase = 0)
    {
        Logger.Trace($"DoodadFuncQuest : skillId {skillId}, QuestKindId {QuestKindId}, QuestId {QuestId}");

        if (caster is not Character character)
            return;

        var isActive = character.Quests.HasQuest(QuestId);
        var isComplete = character.Quests.IsQuestComplete(QuestId);
        var template = QuestManager.Instance.GetTemplate(QuestId);
        var repeatable = template?.Repeatable == true;
        if (!IsEligible(QuestKindId, character, template))
        {
            Logger.Warn($"DoodadFuncQuest rejected: character={character.Name}, doodadTemplate={owner.TemplateId}, " +
                        $"objId={owner.ObjId}, questKind={QuestKindId}, quest={QuestId}, active={isActive}, " +
                        $"complete={isComplete}, repeatable={repeatable}, skill={skillId}");
            character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
            return;
        }

        if (QuestKindId == OfferQuestKind)
            character.SendPacket(new SCDoodadQuestAcceptPacket(owner.ObjId, QuestId));
        else
            QuestManager.Instance.DoReportEvents(character, QuestId, 0, owner.ObjId, 0);
    }
}
