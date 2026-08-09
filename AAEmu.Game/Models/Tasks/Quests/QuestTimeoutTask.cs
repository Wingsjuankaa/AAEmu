using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Tasks.Quests
{
    public class QuestTimeoutTask : Task
    {
        private Character _owner;
        private uint _questId;

        public QuestTimeoutTask(Character owner, uint questId)
        {
            _owner = owner;
            _questId = questId;
        }

        public override void Execute()
        {
            // A completion can race a Quartz callback that was already due.
            // Never emit a timeout or touch state after the quest disappeared.
            if (_owner?.Quests?.HasQuest(_questId) == true)
                QuestManager.Instance.CancelQuest(_owner, _questId);
        }
    }
}
