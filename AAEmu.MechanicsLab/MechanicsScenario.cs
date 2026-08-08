using System;
using System.Collections.Generic;

using Newtonsoft.Json;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsScenario
    {
        [JsonProperty("schema_version")]
        public int SchemaVersion { get; set; } = 1;
        [JsonProperty("name")]
        public string Name { get; set; }
        [JsonProperty("seed")]
        public int Seed { get; set; } = 1;
        [JsonProperty("clock_utc")]
        public DateTime ClockUtc { get; set; } = new DateTime(2021, 12, 14, 12, 0, 0, DateTimeKind.Utc);
        [JsonProperty("dd05_initial")]
        public byte Dd05Initial { get; set; }
        [JsonProperty("actors")]
        public List<MechanicsActorSpec> Actors { get; set; } = new List<MechanicsActorSpec>();
        [JsonProperty("initial_buffs")]
        public List<MechanicsBuffSpec> InitialBuffs { get; set; } = new List<MechanicsBuffSpec>();
        [JsonProperty("actions")]
        public List<MechanicsActionSpec> Actions { get; set; } = new List<MechanicsActionSpec>();
        [JsonProperty("expected")]
        public MechanicsExpectedSpec Expected { get; set; } = new MechanicsExpectedSpec();
    }

    public sealed class MechanicsActorSpec
    {
        [JsonProperty("id")]
        public uint Id { get; set; }
        [JsonProperty("kind")]
        public string Kind { get; set; } = "unit";
        [JsonProperty("template_id")]
        public uint TemplateId { get; set; }
        [JsonProperty("name")]
        public string Name { get; set; }
        [JsonProperty("level")]
        public byte Level { get; set; } = 55;
        [JsonProperty("ability_level")]
        public int AbilityLevel { get; set; } = 55;
        [JsonProperty("hp")]
        public int Hp { get; set; } = 100;
        [JsonProperty("max_hp")]
        public int MaxHp { get; set; } = 100;
        [JsonProperty("mp")]
        public int Mp { get; set; } = 1000;
        [JsonProperty("max_mp")]
        public int MaxMp { get; set; } = 1000;
        [JsonProperty("faction_id")]
        public uint FactionId { get; set; }
        [JsonProperty("x")]
        public float X { get; set; }
        [JsonProperty("y")]
        public float Y { get; set; }
        [JsonProperty("z")]
        public float Z { get; set; }
        [JsonProperty("ranged_dps")]
        public int RangedDps { get; set; } = 500;
        [JsonProperty("ranged_dps_inc")]
        public int RangedDpsInc { get; set; } = 500;
        [JsonProperty("level_dps")]
        public float LevelDps { get; set; } = 100;
        [JsonProperty("ranged_holdable_id")]
        public uint RangedHoldableId { get; set; }
        [JsonProperty("ranged_item_id")]
        public uint RangedItemId { get; set; }
    }

    public sealed class MechanicsBuffSpec
    {
        [JsonProperty("actor_id")]
        public uint ActorId { get; set; }
        [JsonProperty("caster_id")]
        public uint CasterId { get; set; }
        [JsonProperty("buff_id")]
        public uint BuffId { get; set; }
    }

    public sealed class MechanicsActionSpec
    {
        [JsonProperty("type")]
        public string Type { get; set; }
        [JsonProperty("actor_id")]
        public uint ActorId { get; set; }
        [JsonProperty("target_id")]
        public uint TargetId { get; set; }
        [JsonProperty("skill_id")]
        public uint SkillId { get; set; }
        [JsonProperty("milliseconds")]
        public int Milliseconds { get; set; }
        [JsonProperty("x")]
        public float X { get; set; }
        [JsonProperty("y")]
        public float Y { get; set; }
        [JsonProperty("z")]
        public float Z { get; set; }
        [JsonProperty("state")]
        public string State { get; set; }
        [JsonProperty("value")]
        public int Value { get; set; }
    }

    public sealed class MechanicsExpectedSpec
    {
        [JsonProperty("packet_sequence")]
        public List<string> PacketSequence { get; set; } = new List<string>();
        [JsonProperty("packet_absent_after_death")]
        public List<string> PacketAbsentAfterDeath { get; set; } = new List<string>();
        [JsonProperty("death_count")]
        public int? DeathCount { get; set; }
        [JsonProperty("removed_buff_ids")]
        public List<uint> RemovedBuffIds { get; set; } = new List<uint>();
        [JsonProperty("target_hp")]
        public int? TargetHp { get; set; }
        [JsonProperty("require_counter_monotonic_modulo_256")]
        public bool RequireCounterMonotonicModulo256 { get; set; } = true;
        [JsonProperty("require_wire_plaintext_order_match")]
        public bool RequireWirePlaintextOrderMatch { get; set; } = true;
        [JsonProperty("require_no_exceptions")]
        public bool RequireNoExceptions { get; set; } = true;
    }
}
