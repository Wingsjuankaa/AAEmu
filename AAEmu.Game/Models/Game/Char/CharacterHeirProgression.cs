using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Heirs;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Models.Game.Char
{
    public partial class Character
    {
        private readonly object _heirLevelUpLock = new object();

        private bool ApplyHeirExpGain(int expDelta)
        {
            if (expDelta <= 0 || Level < HeirProgressionPolicy.StartLevel)
                return false;

            lock (_heirLevelUpLock)
            {
                var gameData = HeirGameData.Instance;
                var derivedLevel = gameData.GetLevelForExp(HierExp);
                if (derivedLevel != HierLevel)
                {
                    _log.Warn(
                        "AA8 ancestral EXP rejected for {0}: persisted level {1} disagrees with exp-derived level {2} at {3}",
                        Name, HierLevel, derivedLevel, HierExp);
                    return false;
                }

                HierExp = gameData.ApplyExpGain(HierExp, expDelta);
                return gameData.TryGetLevelUpRequirement(Level, HierExp, out var requirement) &&
                       requirement.ReqItemId == 0;
            }
        }

        public bool TryLevelUpHeir()
        {
            lock (_heirLevelUpLock)
            {
                var gameData = HeirGameData.Instance;
                var derivedLevel = gameData.GetLevelForExp(HierExp);
                if (derivedLevel != HierLevel)
                {
                    _log.Warn(
                        "AA8 ancestral level-up rejected for {0}: persisted level {1} disagrees with exp-derived level {2} at {3}",
                        Name, HierLevel, derivedLevel, HierExp);
                    return false;
                }

                if (!gameData.TryGetLevelUpRequirement(Level, HierExp, out var requirement))
                {
                    _log.Info(
                        "AA8 ancestral level-up not ready for {0}: level={1}, ancestralLevel={2}, ancestralExp={3}",
                        Name, Level, HierLevel, HierExp);
                    return false;
                }

                var nextExp = requirement.ReqTotalExp;
                var nextLevel = gameData.GetLevelForExp(nextExp);
                if (nextLevel != HierLevel + 1)
                {
                    _log.Error(
                        "AA8 ancestral catalog boundary is invalid for {0}: level {1}, next {2}, exp {3}",
                        Name, HierLevel, nextLevel, nextExp);
                    return false;
                }

                if (requirement.ReqItemId != 0)
                {
                    if (Inventory == null ||
                        !Inventory.CheckItems(
                            SlotType.Inventory, requirement.ReqItemId, requirement.ReqItemCount))
                    {
                        _log.Info(
                            "AA8 ancestral level-up lacks item for {0}: template={1}, count={2}",
                            Name, requirement.ReqItemId, requirement.ReqItemCount);
                        return false;
                    }

                    var consumed = Inventory.Bag.ConsumeItem(
                        ItemTaskType.UpgradeSkill,
                        requirement.ReqItemId,
                        requirement.ReqItemCount,
                        null);
                    if (consumed != requirement.ReqItemCount)
                    {
                        _log.Error(
                            "AA8 ancestral level-up could not consume the preflighted item for {0}: expected={1}, consumed={2}",
                            Name, requirement.ReqItemCount, consumed);
                        return false;
                    }
                }

                HierExp = nextExp;
                HierLevel = nextLevel;
                BroadcastPacket(new SCHeirLevelUpPacket(ObjId), true);
                SendPacket(new SCListSkillActiveTypsPacket(
                    SkillActiveTypes.BuildPacketEntries()));
                _log.Info(
                    "AA8 ancestral level-up completed for {0}: ancestralLevel={1}, ancestralExp={2}",
                    Name, HierLevel, HierExp);
                return true;
            }
        }
    }
}
