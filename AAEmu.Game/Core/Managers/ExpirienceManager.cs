using System.Collections.Generic;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Utils.DB;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    public class ExpirienceManager : Singleton<ExpirienceManager>
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();

        private Dictionary<byte, ExpirienceLevelTemplate> _levels;

        public int GetExpForLevel(byte level, bool mate = false)
        {
            return _levels.TryGetValue(level, out var template)
                ? mate ? template.TotalMateExp : template.TotalExp
                : 0;
        }

        public byte GetLevelFromExp(int exp, bool mate = false)
        {
            // Loop the levels to find the level for a given exp value
            for (byte lv = 2; lv <= _levels.Count; lv++)
            {
                if (exp < (mate ? _levels[lv].TotalMateExp : _levels[lv].TotalExp))
                    return (byte)(lv - 1);
            }
            return (byte)_levels.Count;
        }

        public int GetExpNeededToGivenLevel(int currentExp, byte targetLevel, bool mate = false)
        {
            var targetexp = GetExpForLevel(targetLevel, mate);
            var diff = targetexp - currentExp;
            return diff <= 0 ? 0 : diff ;
        }

        public int GetSkillPointsForLevel(byte level)
        {
            return _levels.TryGetValue(level, out var template) ? template.SkillPoints : 0;
        }

        public void Load()
        {
            _levels = new Dictionary<byte, ExpirienceLevelTemplate>();
            using (var connection = SQLite.CreateConnection())
            {
                _log.Info("Loading expirience data...");
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM levels";
                    command.Prepare();
                    using (var sqliteDataReader = command.ExecuteReader())
                    using (var reader = new SQLiteWrapperReader(sqliteDataReader))
                    {
                        while (reader.Read())
                        {
                            var level = new ExpirienceLevelTemplate();
                            level.Level = reader.GetByte("id");
                            level.TotalExp = reader.GetInt32("total_exp");
                            level.TotalMateExp = reader.GetInt32("total_mate_exp");
                            level.SkillPoints = reader.GetInt32("skill_points");
                            _levels.Add(level.Level, level);
                        }
                    }
                }

                _log.Info("Expirience data loaded");
            }
        }
    }
}
