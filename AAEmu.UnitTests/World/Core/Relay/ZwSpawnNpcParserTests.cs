using AAEmu.Commons.Network;
using AAEmu.Game;
using AAEmu.Game.Models.Game.Units;
using AAEmu.World.Core.Relay;

namespace AAEmu.UnitTests.World.Core.Relay;

public class ZwSpawnNpcParserTests
{
    [Test]
    public async Task TryParse_PreservesQuestSpawnCharacterContext()
    {
        var raw = BuildCharacterSpawn(
            characterId: 7,
            lifeTime: 60f,
            despawnOnCreatorDeath: true,
            useSummonerAggroTarget: true);

        await Assert.That(raw.Length).IsEqualTo(ZwSpawnNpcParser.AmbientBodyLength);

        var parsed = ZwSpawnNpcParser.TryParse(raw);

        await Assert.That(parsed).IsNotNull();
        await Assert.That(parsed.SpawnerId).IsEqualTo(68410u);
        await Assert.That(parsed.SpawnerType).IsEqualTo(11727u);
        await Assert.That(parsed.TemplateId).IsEqualTo(10564u);
        await Assert.That(parsed.HasNativeSpawnContext).IsTrue();
        await Assert.That(parsed.CreatorIdentityWire.Length).IsEqualTo(17);
        await Assert.That(parsed.CreatorIdentityWire[0]).IsEqualTo((byte)BaseUnitType.Character);
        await Assert.That(BitConverter.ToUInt64(parsed.CreatorIdentityWire, 1)).IsEqualTo(7UL);
        await Assert.That(parsed.SpawnReasonWire).IsEquivalentTo(new byte[] { 0 });
        await Assert.That(parsed.DespawnOnCreatorDeath).IsTrue();
        await Assert.That(parsed.UseSummonerAggroTarget).IsTrue();
        await Assert.That(parsed.LifeTime).IsEqualTo(60f);
        await Assert.That(parsed.IsFactionPermission).IsFalse();
    }

    [Test]
    public async Task WzSpawnContext_ReordersZwFieldsWithoutLosingIdentityOrReason()
    {
        var raw = BuildCharacterSpawn(
            characterId: 0x0102030405060708UL,
            lifeTime: 60f,
            despawnOnCreatorDeath: true,
            useSummonerAggroTarget: true);
        var parsed = ZwSpawnNpcParser.TryParse(raw);
        var stream = new PacketStream();

        var written = WorldIntegration.WriteWzNpcSpawnContextFromWire(
            stream,
            parsed.CreatorIdentityWire,
            parsed.SpawnReasonWire,
            parsed.LifeTime,
            parsed.DespawnOnCreatorDeath,
            parsed.UseSummonerAggroTarget);

        await Assert.That(written).IsTrue();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)BaseUnitType.Character);
        await Assert.That(stream.ReadUInt64()).IsEqualTo(0x0102030405060708UL);
        await Assert.That(stream.ReadInt64()).IsEqualTo(0L);
        await Assert.That(stream.ReadBoolean()).IsTrue();
        await Assert.That(stream.ReadBoolean()).IsTrue();
        await Assert.That(stream.ReadSingle()).IsEqualTo(60f);
        await Assert.That(stream.ReadSByte()).IsEqualTo((sbyte)0);
        await Assert.That(stream.Pos).IsEqualTo(stream.Count);
    }

    [Test]
    public async Task TryParse_LeavesUnknownCreatorUnionFailClosed()
    {
        var raw = BuildCharacterSpawn(
            characterId: 7,
            lifeTime: 60f,
            despawnOnCreatorDeath: true,
            useSummonerAggroTarget: true);
        raw[45] = (byte)BaseUnitType.Slave;

        var parsed = ZwSpawnNpcParser.TryParse(raw);

        await Assert.That(parsed).IsNotNull();
        await Assert.That(parsed.HasNativeSpawnContext).IsFalse();
        await Assert.That(parsed.CreatorIdentityWire).IsEmpty();
        await Assert.That(parsed.SpawnReasonWire).IsEmpty();
    }

    [Test]
    public async Task TryParse_PreservesVariableReasonAfterNativeNames()
    {
        var expectedReason = new byte[] { 6, 0x11, 0x22, 0x33, 0x44 };
        var raw = BuildCharacterSpawn(
            characterId: 7,
            lifeTime: 12.5f,
            despawnOnCreatorDeath: false,
            useSummonerAggroTarget: true,
            summonerName: "Dannia",
            masterName: "Lucius",
            spawnReasonWire: expectedReason);

        var parsed = ZwSpawnNpcParser.TryParse(raw);

        await Assert.That(parsed).IsNotNull();
        await Assert.That(parsed.HasNativeSpawnContext).IsTrue();
        await Assert.That(parsed.SpawnReasonWire).IsEquivalentTo(expectedReason);
        await Assert.That(parsed.DespawnOnCreatorDeath).IsFalse();
        await Assert.That(parsed.UseSummonerAggroTarget).IsTrue();
        await Assert.That(parsed.LifeTime).IsEqualTo(12.5f);
    }

    private static byte[] BuildCharacterSpawn(
        ulong characterId,
        float lifeTime,
        bool despawnOnCreatorDeath,
        bool useSummonerAggroTarget,
        string summonerName = "",
        string masterName = "",
        byte[] spawnReasonWire = null)
    {
        var stream = new PacketStream();
        stream.Write(68410u);
        stream.Write(11727u);
        stream.Write((byte)0);
        stream.Write((byte)0);
        stream.Write((ushort)0);
        stream.Write(10564u);
        stream.Write(0u);
        stream.Write(0u);
        stream.Write((byte)0);
        stream.Write(1122.17f);
        stream.Write(2949.78f);
        stream.Write(122.691f);
        stream.Write(0f);
        stream.Write(1f);

        stream.Write((byte)BaseUnitType.Character);
        stream.Write(characterId);
        stream.Write(0L);
        stream.Write(summonerName);
        stream.Write(masterName);
        stream.Write(0u);
        stream.Write(spawnReasonWire ?? new byte[] { 0 });
        stream.Write(despawnOnCreatorDeath);
        stream.Write(useSummonerAggroTarget);
        stream.Write(lifeTime);
        stream.Write(false);
        return stream.GetBytes();
    }
}
