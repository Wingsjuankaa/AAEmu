using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using AAEmu.Commons.IO;
using AAEmu.Commons.Utils;
using AAEmu.Game.IO;
using AAEmu.Game.Models.Game.Animation;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Mechanics;
using AAEmu.Game.Utils.DB;
using NLog;

namespace AAEmu.Game.Core.Managers
{
    public class AnimationManager : Singleton<AnimationManager>
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();

        private Dictionary<uint, Anim> _animations = new Dictionary<uint, Anim>();
        private Dictionary<string, Anim> _animationsByName = new Dictionary<string, Anim>();
        private Dictionary<string, IReadOnlyDictionary<string, AnimDuration>> _combatSyncByProfile =
            new Dictionary<string, IReadOnlyDictionary<string, AnimDuration>>(StringComparer.OrdinalIgnoreCase);

        public Anim GetAnimation(uint id)
        {
            return _animations.ContainsKey(id) ? _animations[id] : null;
        }

        public Anim GetAnimation(string name)
        {
            return _animationsByName.ContainsKey(name) ? _animationsByName[name] : null;
        }

        public int GetCombatSyncTime(uint animationId, BaseUnit actor)
        {
            var animation = GetAnimation(animationId);
            if (animation == null)
                throw new InvalidOperationException($"AA8 animation {animationId} is not present in the runtime catalog");

            var profile = ResolveCombatSyncProfile(actor);
            if (!_combatSyncByProfile.TryGetValue(profile, out var animations))
            {
                throw new InvalidOperationException(
                    $"AA8 combat-sync profile '{profile}' is absent for animation {animationId} ({animation.Name}); " +
                    $"available=[{string.Join(",", _combatSyncByProfile.Keys.OrderBy(value => value).Take(24))}]");
            }
            if (!animations.TryGetValue(animation.Name, out var timing) || timing.combat_sync_time <= 0)
            {
                throw new InvalidOperationException(
                    $"AA8 combat-sync timing is not proven for profile '{profile}', animation {animationId} ({animation.Name})");
            }
            return timing.combat_sync_time;
        }

        public bool TryGetCombatSyncTime(uint animationId, BaseUnit actor, out int milliseconds)
        {
            milliseconds = 0;
            var animation = GetAnimation(animationId);
            if (animation == null)
                return false;
            var profile = ResolveCombatSyncProfile(actor);
            if (!_combatSyncByProfile.TryGetValue(profile, out var animations) ||
                !animations.TryGetValue(animation.Name, out var timing) ||
                timing.combat_sync_time <= 0)
                return false;
            milliseconds = timing.combat_sync_time;
            return true;
        }

        public static string ResolveCombatSyncProfile(BaseUnit actor)
        {
            if (!(actor is Character character))
                return "nuian_male";

            var race = character.Race.ToString().ToLowerInvariant();
            var gender = character.Gender.ToString().ToLowerInvariant();
            if (character.Race == Race.None || character.Gender == Gender.None)
            {
                // Headless fixtures created before race/gender became part of
                // the combat-sync contract represent the AA8 baseline actor.
                if (MechanicsRuntime.Current != null)
                    return "nuian_male";
                throw new InvalidOperationException("AA8 character has no race/gender combat-sync profile");
            }
            return $"{race}_{gender}";
        }

        /// <summary>
        /// Parse target .g file into a List<AnimCombatSyncEvent>
        /// </summary>
        /// <param name="gFileName"></param>
        /// <returns>Returns null if there is a error, otherwise returns the list</returns>
        private List<AnimCombatSyncEvent> ParseGFile(string gFileName)
        {
            var res = new List<AnimCombatSyncEvent>();
            var lines = ClientFileManager.GetFileAsString(gFileName).Split("\r\n");

            AnimCombatSyncEvent lastCombatSyncEvent = null;
            AnimDuration lastAnimDuration = null;
            for (var n = 0; n < lines.Length; n++)
            {
                var line = lines[n];
                var spaceCount = line.TakeWhile(char.IsWhiteSpace).Count();
                var trimmedLine = line.Trim(' ');
                if (spaceCount == 0)
                {
                    // Start of new model section
                    lastCombatSyncEvent = new AnimCombatSyncEvent();
                    lastCombatSyncEvent.ModelName = line.Trim('"');
                    res.Add(lastCombatSyncEvent);
                    lastAnimDuration = null;
                }
                else if (lastCombatSyncEvent != null && spaceCount == 4)
                {
                    // Start of new animation section
                    lastAnimDuration = new AnimDuration();
                    if (!lastCombatSyncEvent.Animations.TryAdd(trimmedLine, lastAnimDuration))
                    {
                        _log.Warn($"Syntax error in {gFileName} at line {n + 1} : {line}");
                        return null;
                    }
                }
                else if (lastAnimDuration != null && spaceCount == 8)
                {
                    // This is a actual property
                    var props = trimmedLine.Split(' ');
                    if (props.Length != 2)
                    {
                        _log.Warn($"Syntax error in {gFileName} at line {n + 1} : {line}");
                        return null;
                    }
                    else if (props[0] == "total_time")
                    {
                        if (int.TryParse(props[1], out var totTime))
                            lastAnimDuration.total_time = totTime;
                        else
                        {
                            _log.Warn($"int parse error in {gFileName} at line {n + 1} : {line}");
                            return null;
                        }
                    }
                    else if (props[0] == "combat_sync_time")
                    {
                        if (int.TryParse(props[1], out var syncTime))
                            lastAnimDuration.combat_sync_time = syncTime;
                        else
                        {
                            _log.Warn($"int parse error in {gFileName} at line {n + 1} : {line}");
                            return null;
                        }
                    }
                    else
                    {
                        _log.Warn($"Unknown property in {gFileName} at line {n + 1} : {line}");
                    }
                }
                else
                {
                    _log.Warn($"Unknown Syntax in {gFileName} at line {n + 1} : {line}");
                    return null;
                }
            }
            return res;
        }

        public void Load()
        {
            _animations = new Dictionary<uint, Anim>();
            _animationsByName = new Dictionary<string, Anim>();
            _combatSyncByProfile =
                new Dictionary<string, IReadOnlyDictionary<string, AnimDuration>>(StringComparer.OrdinalIgnoreCase);

            _log.Info("Loading animations...");

            using (var connection = SQLite.CreateConnection())
            {
                /* Anims */
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM anims";
                    command.Prepare();
                    using (var reader = new SQLiteWrapperReader(command.ExecuteReader()))
                    {
                        while (reader.Read())
                        {
                            var name = reader.GetString("name", null);
                            if (string.IsNullOrEmpty(name))
                            {
                                _log.Warn($"Skipping animation {reader.GetUInt32("id")} with no native name");
                                continue;
                            }

                            var template = new Anim()
                            {
                                Id = reader.GetUInt32("id"),
                                Name = name,
                                Loop = reader.GetBoolean("loop"),
                                Category = (AnimCategory)reader.GetUInt32("category_id"),
                                RideUB = reader.GetString("ride_ub", string.Empty),
                                HangUB = reader.GetString("hang_ub", string.Empty),
                                SwimUB = reader.GetString("swim_ub", string.Empty),
                                MoveUB = reader.GetString("move_ub", string.Empty),
                                RelaxedUB = reader.GetString("relaxed_ub", string.Empty),
                                SwimMoveUB = reader.GetString("swim_move_ub", string.Empty)
                            };

                            if (_animationsByName.ContainsKey(template.Name)) continue;
                            
                            _animations.Add(template.Id, template);
                            _animationsByName.Add(template.Name, template); // в наличии дубль Nam
                            /*
                             *  id                                                              Name
                             *  835     4   wyvern_ac_coin_launch	0	wyvern_ac_coin_launch	wyvern_ac_coin_launch		wyvern_ac_coin_launch	wyvern_ac_coin_launch	wyvern_ac_coin_launch
                             *  8000021	4   wyvern_ac_coin_launch	0	wyvern_ac_coin_launch	wyvern_ac_coin_launch		wyvern_ac_coin_launch	wyvern_ac_coin_launch	wyvern_ac_coin_launch
                             */
                        }
                    }
                }
            }

            // Load animation durations from client data
            var gFileName = "game/combat_sync_event_list.g"; 
            var combatSyncEvents = ParseGFile(gFileName);

            if (combatSyncEvents == null)
            {
                _log.Fatal($"Error reading {gFileName}");
                return;
            }
            
            // Preserve every AA8 model/skeleton profile. Plot add_anim_cs_time
            // resolves against the casting character instead of silently
            // inheriting nuian_male or a zero marker.
            foreach (var cse in combatSyncEvents)
            {
                _combatSyncByProfile[cse.ModelName] = cse.Animations;
                if (cse.ModelName == "nuian_male")
                {
                    // Copy stuff
                    foreach (var (animKey,animVal) in cse.Animations)
                    {
                        if (_animationsByName.TryGetValue(animKey, out var anim))
                        {
                            anim.Duration = animVal.total_time;
                            anim.CombatSyncTime = animVal.combat_sync_time;
                        }
                    }
                }
            }
            _log.Info("Loaded AA8 combat-sync profiles: {0}",
                string.Join(",", _combatSyncByProfile.Keys.OrderBy(value => value)));
        }
    }
}
