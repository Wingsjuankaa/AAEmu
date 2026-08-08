using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;

using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Models.Game.AI.v2.AiCharacters;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.World;
using AAEmu.Game.Models.Mechanics;

namespace AAEmu.MechanicsLab
{
    public sealed class MechanicsArena : IMechanicsWorld, IMechanicsDeathSink
    {
        private readonly Dictionary<uint, GameObject> _objects = new Dictionary<uint, GameObject>();
        private readonly MechanicsTimeline _timeline;

        public int NpcDeathCount { get; private set; }
        public int ExperienceEvents { get; private set; }
        public int AggroCleanupCount { get; private set; }
        public int TargetCleanupCount { get; private set; }

        public MechanicsArena(MechanicsTimeline timeline)
        {
            _timeline = timeline;
        }

        public void Add(GameObject gameObject)
        {
            _objects.Add(gameObject.ObjId, gameObject);
        }

        public GameObject GetGameObject(uint objId) =>
            _objects.TryGetValue(objId, out var value) ? value : null;

        public BaseUnit GetBaseUnit(uint objId) => GetGameObject(objId) as BaseUnit;
        public Unit GetUnit(uint objId) => GetGameObject(objId) as Unit;

        public IReadOnlyList<GameObject> GetAround(GameObject origin, float? radius, bool useModelSize)
        {
            var query = _objects.Values.Where(candidate => candidate.ObjId != origin.ObjId);
            if (radius.HasValue)
            {
                var effectiveRadius = radius.Value + (useModelSize ? origin.ModelSize : 0f);
                var squared = effectiveRadius * effectiveRadius;
                query = query.Where(candidate =>
                {
                    var dx = candidate.Transform.World.Position.X - origin.Transform.World.Position.X;
                    var dy = candidate.Transform.World.Position.Y - origin.Transform.World.Position.Y;
                    var dz = candidate.Transform.World.Position.Z - origin.Transform.World.Position.Z;
                    var candidateRadius = useModelSize ? candidate.ModelSize : 0f;
                    return dx * dx + dy * dy + dz * dz <=
                           (effectiveRadius + candidateRadius) * (effectiveRadius + candidateRadius);
                });
            }
            return query.OrderBy(candidate => candidate.ObjId).ToList();
        }

        public void RecordNpcDeath(Npc npc, Unit killer)
        {
            NpcDeathCount++;
            ExperienceEvents++;
            if (npc.AggroTable.Count == 0)
                AggroCleanupCount++;
            if (npc.CurrentTarget == null && (killer == null || killer.CurrentTarget == null))
                TargetCleanupCount++;
            _timeline.Add("npc_death", npc.ObjId, killer?.ObjId ?? 0, null);
            _timeline.Add("experience_awarded", killer?.ObjId ?? 0, npc.ObjId, null);
        }

        public List<string> FindInvalidDeadUnitReferences()
        {
            var invalid = new List<string>();
            foreach (var deadNpc in _objects.Values.OfType<Npc>().Where(npc => npc.Hp <= 0))
            {
                if (deadNpc.CurrentTarget != null)
                    invalid.Add($"npc:{deadNpc.ObjId}:current_target:{deadNpc.CurrentTarget.ObjId}");
                foreach (var aggroId in deadNpc.AggroTable.Keys.OrderBy(id => id))
                    invalid.Add($"npc:{deadNpc.ObjId}:aggro:{aggroId}");

                foreach (var unit in _objects.Values.OfType<Unit>()
                             .Where(unit => unit.ObjId != deadNpc.ObjId && unit.CurrentTarget?.ObjId == deadNpc.ObjId))
                    invalid.Add($"unit:{unit.ObjId}:current_target:dead:{deadNpc.ObjId}");
            }
            return invalid;
        }

        public MechanicsCharacter CreateCharacter(
            MechanicsActorSpec spec,
            GameConnection connection)
        {
            var character = new MechanicsCharacter(spec.AbilityLevel)
            {
                ObjId = spec.Id,
                Name = spec.Name ?? $"Character-{spec.Id}",
                Level = spec.Level,
                Hp = spec.Hp,
                MaxHp = spec.MaxHp,
                Mp = spec.Mp,
                MaxMp = spec.MaxMp,
                RangedDps = spec.RangedDps,
                RangedDpsInc = spec.RangedDpsInc,
                LevelDps = spec.LevelDps,
                Connection = connection,
                Ability1 = AbilityType.Wild,
                Ability2 = AbilityType.Magic,
                Ability3 = AbilityType.Illusion,
                Faction = CreateFaction(spec.FactionId),
                Procs = null
            };
            character.Procs = new UnitProcs(character);
            character.Abilities = new CharacterAbilities(character);
            character.Quests = new CharacterQuests(character);
            character.Inventory = new Inventory(character);
            SetPosition(character, spec);
            if (spec.RangedHoldableId > 0)
                EquipRanged(character, spec.RangedItemId, spec.RangedHoldableId);
            Add(character);
            connection.ActiveChar = character;
            return character;
        }

        public MechanicsNpc CreateNpc(MechanicsActorSpec spec)
        {
            var template = NpcManager.Instance.GetTemplate(spec.TemplateId) ??
                           throw new InvalidOperationException(
                               $"NPC template {spec.TemplateId} is absent from the active AA8 compact");
            var npc = new MechanicsNpc
            {
                ObjId = spec.Id,
                TemplateId = spec.TemplateId,
                Name = spec.Name ?? $"Npc-{spec.TemplateId}",
                Level = spec.Level,
                Hp = spec.Hp,
                MaxHp = spec.MaxHp,
                Mp = spec.Mp,
                MaxMp = spec.MaxMp,
                Faction = CreateFaction(spec.FactionId),
                Template = template
            };
            npc.Ai = new DummyAiCharacter {Owner = npc};
            npc.Ai.Start();
            SetPosition(npc, spec);
            Add(npc);
            return npc;
        }

        public void MakeHostile(Unit source, Unit target)
        {
            if (source.Faction == null || target.Faction == null)
                return;
            source.Faction.Relations[target.Faction.Id] = new FactionRelation
            {
                Id = source.Faction.Id,
                Id2 = target.Faction.Id,
                State = RelationState.Hostile
            };
            target.Faction.Relations[source.Faction.Id] = new FactionRelation
            {
                Id = target.Faction.Id,
                Id2 = source.Faction.Id,
                State = RelationState.Hostile
            };
        }

        private static SystemFaction CreateFaction(uint id) => new SystemFaction
        {
            Id = id == 0 ? 1u : id,
            Name = $"LabFaction-{id}"
        };

        private static void SetPosition(GameObject actor, MechanicsActorSpec spec)
        {
            actor.Transform.Local.SetPosition(spec.X, spec.Y, spec.Z, 0f, 0f, 0f);
        }

        private static void EquipRanged(Unit unit, uint itemId, uint holdableId)
        {
            var resolvedItemId = itemId == 0 ? 50799u : itemId;
            var template = ItemManager.Instance.GetTemplate(resolvedItemId) as WeaponTemplate ??
                           throw new InvalidOperationException(
                               $"Ranged item {resolvedItemId} is not a weapon in the active AA8 compact");
            if (template.HoldableTemplate == null ||
                (holdableId != 0 && template.HoldableTemplate.Id != holdableId &&
                 template.HoldableTemplate.KindId != holdableId))
                throw new InvalidOperationException(
                    $"Ranged item {resolvedItemId} does not satisfy holdable {holdableId}");
            var weapon = new Weapon
            {
                Id = 1,
                TemplateId = template.Id,
                Template = template,
                Count = 1,
                Slot = (int)EquipmentItemSlot.Ranged,
                SlotType = SlotType.Equipment,
                GemIds = new uint[18]
            };
            unit.Equipment.AddOrMoveExistingItem(
                ItemTaskType.Invalid,
                weapon,
                (int)EquipmentItemSlot.Ranged);
        }
    }

    public sealed class MechanicsCharacter : Character
    {
        private readonly int _abilityLevel;
        private float _levelDps;
        private int _rangedDps;
        private int _rangedDpsInc;

        public MechanicsCharacter(int abilityLevel) : base(null)
        {
            _abilityLevel = abilityLevel;
        }

        public override int GetAbLevel(AbilityType type) => _abilityLevel;
        public override float LevelDps
        {
            get => _levelDps;
            set => _levelDps = value;
        }

        public override int RangedDps
        {
            get => _rangedDps;
            set => _rangedDps = value;
        }

        public override int RangedDpsInc
        {
            get => _rangedDpsInc;
            set => _rangedDpsInc = value;
        }

        public override float ModelSize { get; set; }
    }

    public sealed class MechanicsNpc : Npc
    {
        public override float ModelSize { get; set; }
    }
}
