using System;
using System.Collections.Generic;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Quests.Templates;
using AAEmu.Game.Models.Tasks.Quests;

namespace AAEmu.Game.Models.Game.Quests.Acts
{
    public class QuestActCheckTimer : QuestActTemplate
    {
        public int LimitTime { get; set; }
        public bool ForceChangeComponent { get; set; }
        public uint NextComponent { get; set; }
        public bool PlaySkill { get; set; }
        public uint SkillId { get; set; }
        public bool CheckBuff { get; set; }
        public uint BuffId { get; set; }
        public bool SustainBuff { get; set; }
        public uint TimerNpcId { get; set; }
        public bool IsSkillPlayer { get; set; }

        public override bool Use(Character character, Quest quest, int objective)
        {
            // `objective` is a quest counter, not the native timeout. AA8
            // stores the limit in this detail row and persists the absolute
            // deadline through Quest.WriteData().
            return QuestManager.Instance.ScheduleQuestTimeout(
                character,
                quest,
                LimitTime,
                false,
                true);
        }
    }
}
