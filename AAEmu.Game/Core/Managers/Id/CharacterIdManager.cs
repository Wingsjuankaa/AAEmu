using AAEmu.Commons.Utils;
using AAEmu.Game.Utils;

using Microsoft.Extensions.DependencyInjection;

namespace AAEmu.Game.Core.Managers.Id;

public class CharacterIdManager() : IdManager("CharacterIdManager", FirstId, LastId, ObjTables, Exclude), ICharacterIdManager
{
    private static CharacterIdManager _instance;
    // AA10 x2game-dev!FUN_3971c0c0 reserves housing owner ids below 1000 for
    // native special/fallback ownership. Character ids must live in the literal
    // owner domain or a private house owner is resolved as zero by the client.
    private const uint FirstId = 0x000003E8;
    private const uint LastId = 0x00FFFFFF;
    private static readonly uint[] Exclude = [];
    private static readonly string[,] ObjTables = { { "characters", "id" }, { "slaves", "id" } };

    public static CharacterIdManager Instance =>
        _instance ??= SingletonContainer.ServiceProvider?.GetService<CharacterIdManager>() ?? new CharacterIdManager();
}
