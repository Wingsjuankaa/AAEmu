using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Tasks.Quests;

/// <summary>
/// Delays Ready-context replay until the AA10 client has loaded the entered
/// cell and registered client-only doodad QuestReact callbacks.
/// </summary>
public class ClientDoodadQuestReactResyncTask(
    Character character,
    uint subZoneId,
    long edgeVersion) : Task
{
    public override void Execute()
    {
        if (!character.IsOnline)
            return;

        character.Quests.TryResyncReadyClientDoodadQuestReacts(subZoneId, edgeVersion);
    }
}
