using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

/// <summary>
/// Native client-local doodad phase transition driven by one character's quest state.
/// The shared server doodad must not execute this as a world phase mutation; interaction
/// routing resolves these transitions per character in <see cref="Doodad"/>.
/// </summary>
public class DoodadFuncQuestReact : DoodadPhaseFuncTemplate
{
    public uint QuestId { get; set; }
    public QuestStatus QuestStatus { get; set; }
    public int NextPhase { get; set; }
    public uint QuestComponentId { get; set; }
    public bool BubbleOnce { get; set; }
    public uint BubbleId { get; set; }

    public bool Matches(QuestStatus status, uint componentId)
        => status == QuestStatus && (QuestComponentId == 0 || QuestComponentId == componentId);

    public override bool Use(BaseUnit caster, Doodad owner)
    {
        // QuestReact is evaluated by each client and therefore cannot safely mutate the
        // shared doodad phase here. Server-side interaction routing consumes this template.
        return false;
    }
}
