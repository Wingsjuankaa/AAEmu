using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Tasks.Skills;

public class CraftTask(Character character, uint craftId, uint objId, long generation) : Task
{
    public override void Execute()
    {
        if (!Cancelled && character is not null)
            character.Craft.TryContinue(craftId, objId, generation);
    }
}
