using AAEmu.Game.Core.Managers;

namespace AAEmu.Game.Models.Game.Quests;

public partial class Quest
{
    private readonly List<QuestRewardLedgerKey> _deferredRewardActs = [];

    internal void TrackDeferredRewardAct(QuestRewardLedgerKey key)
    {
        if (!_deferredRewardActs.Contains(key))
            _deferredRewardActs.Add(key);
    }

    private bool StageDeferredRewardActsForSave()
    {
        if (_deferredRewardActs.Count == 0)
            return true;
        if (Owner is not AAEmu.Game.Models.Game.Char.Character character)
            return false;
        character.Quests.StageRewardLedgerCompletions(_deferredRewardActs);
        _deferredRewardActs.Clear();
        return true;
    }
}
