using AAEmu.Game.Models.Game.DoodadObj.Templates;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.Enums;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.DoodadObj.Funcs;

/// <summary>
/// r575 doodad_func_spawns: NPC interaction spawns use the existing AA10 Zone
/// publication/cleanup path. Do not create a second Game-owned AI as in AA8.
/// </summary>
public class DoodadFuncSpawn : DoodadFuncTemplate
{
    public BaseUnitType OwnerTypeId { get; set; }
    public uint SubType { get; set; }
    public uint PosDirId { get; set; }
    public float PosAngleMin { get; set; }
    public float PosAngleMax { get; set; }
    public float PosDistanceMin { get; set; }
    public float PosDistanceMax { get; set; }
    public uint OriDirId { get; set; }
    public float OriAngle { get; set; }
    public bool UseSummonerFaction { get; set; }
    public float LifeTime { get; set; }
    public bool DespawnOnCreatorDeath { get; set; }
    public bool UseSummonerAggroTarget { get; set; }
    public MateState MateStateId { get; set; }

    public override void Use(BaseUnit caster, Doodad owner, uint skillId, int nextPhase = 0)
    {
        var spawned = ApplySpawn(caster, owner, WorldIntegration.ZoneAuthority,
            (effect, source, target) => effect.SpawnNpcInZone(source, target, null));
        if (!spawned && caster is Character character)
        {
            // InteractionEffect must not count a rejected invocation as quest progress.
            character.SkillCancelled = true;
            character.SendErrorMessage(ErrorMessageType.NoInteractionAvailable);
        }
    }

    internal bool ApplySpawn(BaseUnit caster, Doodad owner, bool zoneAuthority,
        Func<SpawnEffect, BaseUnit, BaseUnit, bool> publish)
    {
        if (owner == null)
            return false;
        owner.ToNextPhase = false;
        if (!zoneAuthority || caster?.Transform == null || owner.Transform == null ||
            publish == null || !TryCreateEffect(out var effect))
        {
            Logger.Warn("DoodadFuncSpawn unsupported closure: func={0}, ownerType={1}, subtype={2}, zone={3}",
                Id, OwnerTypeId, SubType, zoneAuthority);
            return false;
        }

        // Failure includes absent Zone delivery: SpawnNpcInZone removes its mirror
        // in that case. Keep the interaction phase available for a later retry.
        owner.ToNextPhase = publish(effect, caster, owner);
        return owner.ToNextPhase;
    }

    internal bool TryCreateEffect(out SpawnEffect effect)
    {
        effect = null;
        // All NPC rows in r575 use fixed angle/distance intervals. Random ranges,
        // slave/mate ownership and other directions need their own native closure.
        if (OwnerTypeId != BaseUnitType.Npc || SubType == 0 ||
            PosDirId is not (1 or 2) || OriDirId is not (1 or 2) ||
            !float.IsFinite(PosAngleMin) || PosAngleMin != PosAngleMax ||
            !float.IsFinite(PosDistanceMin) || PosDistanceMin < 0 || PosDistanceMin != PosDistanceMax ||
            !float.IsFinite(OriAngle) || !float.IsFinite(LifeTime) || LifeTime < 0)
            return false;

        effect = new SpawnEffect
        {
            OwnerTypeId = OwnerTypeId, SubType = SubType, PosDirId = PosDirId,
            PosAngle = PosAngleMin, PosDistance = PosDistanceMin,
            OriDirId = OriDirId, OriAngle = OriAngle, UseSummonerFaction = UseSummonerFaction,
            LifeTime = LifeTime, DespawnOnCreatorDeath = DespawnOnCreatorDeath,
            UseSummonerAggroTarget = UseSummonerAggroTarget, MateStateId = MateStateId
        };
        return true;
    }
}
