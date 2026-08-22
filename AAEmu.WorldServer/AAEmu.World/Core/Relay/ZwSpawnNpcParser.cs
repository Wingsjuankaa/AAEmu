using System.Buffers.Binary;

using AAEmu.Commons.Network;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.World.Core.Relay;

/// <summary>
/// Wire (ambient 78 B): u32 sid, u32 sType, u8 mIdx, u8 pIdx, u16 tIdx, u32 templateId,
/// group, f32 x,y,z, f32 zRot, f32 scale, BaseUnit creator, two strings, faction,
/// NpcSpawnReason, despawn/use-summoner flags, lifeTime and faction-permission.
/// Optional ISerialize groups are written without a presence byte on this path.
/// Zone does not put a client bcId in this packet — World assigns one.
/// </summary>
public sealed class ZwSpawnNpcParsed
{
    public uint SpawnerId { get; init; }
    public uint SpawnerType { get; init; }
    public byte MemberIdx { get; init; }
    public byte PartIdx { get; init; }
    public ushort TableIdx { get; init; }
    public uint TemplateId { get; init; }
    public uint GroupType { get; init; }
    public uint GroupId { get; init; }
    public byte GroupMemberIdx { get; init; }
    public float X { get; init; }
    public float Y { get; init; }
    public float Z { get; init; }
    public float ZRot { get; init; }
    public float Scale { get; init; }
    public byte[] CreatorIdentityWire { get; init; } = [];
    public byte[] SpawnReasonWire { get; init; } = [];
    public bool DespawnOnCreatorDeath { get; init; }
    public bool UseSummonerAggroTarget { get; init; }
    public float LifeTime { get; init; }
    public bool IsFactionPermission { get; init; }

    public bool HasNativeSpawnContext =>
        CreatorIdentityWire is { Length: > 0 } && SpawnReasonWire is { Length: > 0 };
}

public static class ZwSpawnNpcParser
{
    private const int KnownCreatorIdentityWireLength = 17;
    private const int FixedSpawnContextSuffixLength = 7;

    /// <summary>Minimum body for the fixed header and placement (sid…scale).</summary>
    public const int MinBodyLength = 45;

    /// <summary>Retail ambient body size with empty names, default reason and zero context.</summary>
    public const int AmbientBodyLength = 78;

    public static ZwSpawnNpcParsed? TryParse(byte[] raw)
    {
        // Ambient is 78 B; event OnEvent may append creator fields. Soft-cap avoids UnitState dumps.
        if (raw == null || raw.Length < MinBodyLength || raw.Length > 512)
            return null;

        try
        {
            var s = new PacketStream();
            s.Insert(0, raw);

            var sid = s.ReadUInt32();
            var sType = s.ReadUInt32();
            var mIdx = s.ReadByte();
            var pIdx = s.ReadByte();
            var tIdx = s.ReadUInt16();
            var templateId = s.ReadUInt32();

            var groupType = s.ReadUInt32();
            var groupId = s.ReadUInt32();
            var groupMemberIdx = s.ReadByte();

            // pos is vec3 f32 (ISerialize vt+208), not 11-byte quantized worldPos
            var x = s.ReadSingle();
            var y = s.ReadSingle();
            var z = s.ReadSingle();
            var zRot = s.ReadSingle();
            var scale = s.ReadSingle();

            TryParseSpawnContext(
                raw,
                s.Pos,
                out var creatorIdentityWire,
                out var spawnReasonWire,
                out var despawnOnCreatorDeath,
                out var useSummonerAggroTarget,
                out var lifeTime,
                out var isFactionPermission);

            // Type-2 group path sometimes writes template 0; resolve first Npc member from sType.
            if (templateId == 0 && sType != 0)
                templateId = ResolveTemplateFromSpawnerType(sType);

            if (templateId == 0)
                return null;

            return new ZwSpawnNpcParsed
            {
                SpawnerId = sid,
                SpawnerType = sType,
                MemberIdx = mIdx,
                PartIdx = pIdx,
                TableIdx = tIdx,
                TemplateId = templateId,
                GroupType = groupType,
                GroupId = groupId,
                GroupMemberIdx = groupMemberIdx,
                X = x,
                Y = y,
                Z = z,
                ZRot = zRot,
                Scale = scale <= 0f ? 1f : scale,
                CreatorIdentityWire = creatorIdentityWire,
                SpawnReasonWire = spawnReasonWire,
                DespawnOnCreatorDeath = despawnOnCreatorDeath,
                UseSummonerAggroTarget = useSummonerAggroTarget,
                LifeTime = lifeTime,
                IsFactionPermission = isFactionPermission
            };
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Peek sid/sType for TRACE when full parse fails.</summary>
    public static bool TryPeekIds(byte[] raw, out uint spawnerId, out uint spawnerType)
    {
        spawnerId = 0;
        spawnerType = 0;
        if (raw == null || raw.Length < 8)
            return false;
        spawnerId = BitConverter.ToUInt32(raw, 0);
        spawnerType = BitConverter.ToUInt32(raw, 4);
        return true;
    }

    private static bool TryParseSpawnContext(
        byte[] raw,
        int creatorOffset,
        out byte[] creatorIdentityWire,
        out byte[] spawnReasonWire,
        out bool despawnOnCreatorDeath,
        out bool useSummonerAggroTarget,
        out float lifeTime,
        out bool isFactionPermission)
    {
        creatorIdentityWire = [];
        spawnReasonWire = [];
        despawnOnCreatorDeath = false;
        useSummonerAggroTarget = false;
        lifeTime = 0f;
        isFactionPermission = false;

        if (creatorOffset < 0 || creatorOffset >= raw.Length)
            return false;

        // AA10 r575 BaseUnit identities for Character and Npc both occupy 17 wire bytes.
        // Other union arms have different layouts and remain fail-closed until proven.
        var creatorType = (BaseUnitType)raw[creatorOffset];
        if (creatorType is not (BaseUnitType.Character or BaseUnitType.Npc))
            return false;

        var cursor = creatorOffset + KnownCreatorIdentityWireLength;
        if (cursor > raw.Length
            || !TrySkipString(raw, ref cursor)
            || !TrySkipString(raw, ref cursor))
            return false;

        // faction u32 precedes the variable NpcSpawnReason payload. The final seven bytes are
        // invariant: two bools, lifeTime f32 and isFactionPermission bool.
        if (cursor + sizeof(uint) + sizeof(sbyte) + FixedSpawnContextSuffixLength > raw.Length)
            return false;
        cursor += sizeof(uint);

        var flagsOffset = raw.Length - FixedSpawnContextSuffixLength;
        if (cursor >= flagsOffset)
            return false;

        creatorIdentityWire = raw.AsSpan(creatorOffset, KnownCreatorIdentityWireLength).ToArray();
        spawnReasonWire = raw.AsSpan(cursor, flagsOffset - cursor).ToArray();
        despawnOnCreatorDeath = raw[flagsOffset] != 0;
        useSummonerAggroTarget = raw[flagsOffset + 1] != 0;
        lifeTime = BitConverter.Int32BitsToSingle(
            BinaryPrimitives.ReadInt32LittleEndian(raw.AsSpan(flagsOffset + 2, sizeof(float))));
        isFactionPermission = raw[flagsOffset + 6] != 0;
        return true;
    }

    private static bool TrySkipString(byte[] raw, ref int cursor)
    {
        if (cursor < 0 || cursor + sizeof(short) > raw.Length)
            return false;

        var length = BinaryPrimitives.ReadInt16LittleEndian(raw.AsSpan(cursor, sizeof(short)));
        cursor += sizeof(short);
        if (length < 0 || cursor + length > raw.Length)
            return false;

        cursor += length;
        return true;
    }

    private static uint ResolveTemplateFromSpawnerType(uint spawnerType)
    {
        try
        {
            var template = NpcGameData.Instance.GetNpcSpawnerTemplate(spawnerType);
            if (template?.Npcs == null)
                return 0;

            foreach (var member in template.Npcs)
            {
                if (member == null || member.MemberId == 0)
                    continue;
                if (string.Equals(member.MemberType, "Npc", StringComparison.OrdinalIgnoreCase))
                    return member.MemberId;
            }

            // NpcGroup wire with templateId 0 — leave reject for non-Npc membership.
            // Member Npc templates may still sit inside group tables only if desc expands them
            // differently; World will still TRACE reject for pure groups with zero template.
        }
        catch
        {
            // GameData not ready — reject as before.
        }

        return 0;
    }
}
