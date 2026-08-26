using AAEmu.Game.Models.Game.Crafts;

namespace AAEmu.Game.Core.Managers;

public interface ICraftManager : ILoadable
{
    bool TryGetCraft(uint craftId, out Craft craft);
    bool HasCraft(uint craftId);
}
