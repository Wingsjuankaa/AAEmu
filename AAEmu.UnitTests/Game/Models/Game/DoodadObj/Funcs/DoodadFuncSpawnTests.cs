using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.Enums;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj.Funcs;

public class DoodadFuncSpawnTests
{
    // Native r575 doodad_func_spawns 9, 15 and 24. Fixed descriptor inputs,
    // independent from the implementation's defaults.
    [Test]
    [Arguments(9u, 5797u, 0f, 5f, 2u, 15f, true, false)]
    [Arguments(15u, 4786u, 0f, 1f, 1u, 25f, true, false)]
    [Arguments(24u, 1610u, 180f, 3f, 2u, 90f, false, true)]
    public async Task NativeQuestDescriptors_PreserveZoneSpawnContract(uint id, uint npc,
        float angle, float distance, uint orientation, float lifetime, bool diesWithCreator, bool aggro)
    {
        var func = Native(id, npc, angle, distance, orientation, lifetime, diesWithCreator, aggro);
        await Assert.That(func.TryCreateEffect(out var effect)).IsTrue();
        await Assert.That(effect.OwnerTypeId).IsEqualTo(BaseUnitType.Npc);
        await Assert.That(effect.SubType).IsEqualTo(npc);
        await Assert.That(effect.PosDirId).IsEqualTo(2u);
        await Assert.That(effect.PosAngle).IsEqualTo(angle);
        await Assert.That(effect.PosDistance).IsEqualTo(distance);
        await Assert.That(effect.OriDirId).IsEqualTo(orientation);
        await Assert.That(effect.OriAngle).IsEqualTo(0f);
        await Assert.That(effect.LifeTime).IsEqualTo(lifetime);
        await Assert.That(effect.DespawnOnCreatorDeath).IsEqualTo(diesWithCreator);
        await Assert.That(effect.UseSummonerAggroTarget).IsEqualTo(aggro);
        await Assert.That(effect.UseSummonerFaction).IsFalse();
        await Assert.That(effect.MateStateId).IsEqualTo(MateState.Aggressive);
    }

    [Test]
    public async Task FailedDelivery_DoesNotAdvance_AndRetryPublishesOnce()
    {
        var func = Native(15, 4786, 0, 1, 1, 25, true, false);
        var caster = new Npc();
        var owner = new Doodad { ToNextPhase = true };
        var calls = 0;
        var accepted = false;
        bool Publish(SpawnEffect effect, BaseUnit source, BaseUnit target)
        {
            if (!ReferenceEquals(source, caster) || !ReferenceEquals(target, owner))
                throw new InvalidOperationException("Lost the interaction's source/target");
            calls++;
            return accepted;
        }
        await Assert.That(func.ApplySpawn(caster, owner, true, Publish)).IsFalse();
        await Assert.That(owner.ToNextPhase).IsFalse();
        await Assert.That(calls).IsEqualTo(1);
        accepted = true;
        await Assert.That(func.ApplySpawn(caster, owner, true, Publish)).IsTrue();
        await Assert.That(owner.ToNextPhase).IsTrue();
        await Assert.That(calls).IsEqualTo(2);
    }

    [Test]
    public async Task UnsupportedOrNonZoneSpawn_HasNoSideEffects()
    {
        var func = Native(15, 4786, 0, 1, 1, 25, true, false);
        var caster = new Npc();
        var owner = new Doodad { ToNextPhase = true };
        bool Unexpected(SpawnEffect effect, BaseUnit source, BaseUnit target) =>
            throw new InvalidOperationException("Unsupported descriptor reached publication");
        await Assert.That(func.ApplySpawn(caster, owner, false, Unexpected)).IsFalse();
        await Assert.That(owner.ToNextPhase).IsFalse();
        func.OwnerTypeId = BaseUnitType.Slave;
        await Assert.That(func.ApplySpawn(caster, owner, true, Unexpected)).IsFalse();
        func.OwnerTypeId = BaseUnitType.Npc;
        func.PosDistanceMax = 2;
        await Assert.That(func.ApplySpawn(caster, owner, true, Unexpected)).IsFalse();
        func.PosDistanceMax = 1;
        func.OriDirId = 99;
        await Assert.That(func.ApplySpawn(caster, owner, true, Unexpected)).IsFalse();
        func.OriDirId = 1;
        func.LifeTime = float.NaN;
        await Assert.That(func.ApplySpawn(caster, owner, true, Unexpected)).IsFalse();
        await Assert.That(owner.ToNextPhase).IsFalse();
    }

    private static DoodadFuncSpawn Native(uint id, uint npc, float angle, float distance,
        uint orientation, float lifetime, bool diesWithCreator, bool aggro) => new()
    {
        Id = id, OwnerTypeId = BaseUnitType.Npc, SubType = npc,
        PosDirId = 2, PosAngleMin = angle, PosAngleMax = angle,
        PosDistanceMin = distance, PosDistanceMax = distance,
        OriDirId = orientation, OriAngle = 0, LifeTime = lifetime,
        DespawnOnCreatorDeath = diesWithCreator, UseSummonerAggroTarget = aggro,
        UseSummonerFaction = false, MateStateId = MateState.Aggressive
    };
}
