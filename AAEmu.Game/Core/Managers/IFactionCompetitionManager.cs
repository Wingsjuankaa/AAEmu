using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World.Zones;

namespace AAEmu.Game.Core.Managers;

public interface IFactionCompetitionManager : ILoadable
{
    void OnZoneStateChanged(ushort zoneGroupId, ZoneConflictType previous, ZoneConflictType current, DateTime endsAt);
    void OnTowerDefStarted(uint towerDefId, ushort zoneGroupId, DateTime endsAt);
    void OnTowerDefEnded(uint towerDefId, ushort zoneGroupId);
    void OnPcKill(BaseUnit killer, ushort zoneGroupId);
    void OnNpcKill(Character creditOwner, Npc victim, ushort zoneGroupId);
    void OnQuestCompleted(Character character, uint questId);
    void GiveSpecialPoint(BaseUnit actor, uint amount);
    void SyncToCharacter(Character character);
}
