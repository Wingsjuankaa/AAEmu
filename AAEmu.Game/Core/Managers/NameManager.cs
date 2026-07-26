using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using AAEmu.Commons.Utils;
using AAEmu.Game.Models;
using AAEmu.Game.Utils.DB;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    public class NameManager : Singleton<NameManager>
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();

        private Regex _characterNameRegex;
        private Dictionary<uint, string> _characterNames;

        public string GetCharacterName(uint characterId)
        {
            if (_characterNames.ContainsKey(characterId))
                return _characterNames[characterId].FirstCharToUpper();
            return null;
        }

        public uint GetCharacterId(string characterName)
        {
            var res = (from x in _characterNames where x.Value.ToLower() == characterName.ToLower() select x.Key).FirstOrDefault();
            return res ;
        }

        public NameManager()
        {
            _characterNames = new Dictionary<uint, string>();
        }

        public void Load()
        {
            _characterNameRegex = new Regex(AppConfiguration.Instance.CharacterNameRegex, RegexOptions.Compiled);
            using (var connection = MySQL.CreateConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT id, name FROM characters";
                    command.Prepare();
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                            _characterNames.Add(reader.GetUInt32("id"), reader.GetString("name").ToLower());
                    }
                }
            }

            _log.Info("Loaded {0} character names", _characterNames.Count);
        }

        public byte ValidationCharacterName(string name)
        {
            if (name == "" || !_characterNameRegex.IsMatch(name)) // TODO ...
                return 5; // Это имя содержит недопустимую лексику.
            lock (_characterNames)
            {
                if (_characterNames.Values.Contains(name.ToLowerInvariant()))
                    return 4; // Персонаж с таким именем уже существует. Выберите другое имя.
            }
            return 0;
        }

        public bool TryReserveCharacterName(uint characterId, string name, out byte validationCode)
        {
            validationCode = 0;
            if (string.IsNullOrEmpty(name) || !_characterNameRegex.IsMatch(name))
            {
                validationCode = 5;
                return false;
            }

            var normalized = name.ToLowerInvariant();
            lock (_characterNames)
            {
                if (_characterNames.Values.Contains(normalized))
                {
                    validationCode = 4;
                    return false;
                }
                _characterNames.Add(characterId, normalized);
                return true;
            }
        }

        public void AddCharacterName(uint characterId, string name)
        {
            lock (_characterNames)
                _characterNames.Add(characterId, name.ToLowerInvariant());
        }

        public void RemoveCharacterName(uint characterId)
        {
            lock (_characterNames)
                _characterNames.Remove(characterId);
        }
    }
}
