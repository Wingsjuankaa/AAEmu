using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;

namespace AAEmu.Game.Models.Game.Skills;

public enum SkillObjectType
{
    None = 0,
    Unk1 = 1,
    Unk2 = 2,
    Unk3 = 3,
    Unk4 = 4,
    Unk5 = 5,
    /// <summary>Regrade/Temper support context in r575.</summary>
    ItemGradeEnchantingSupport = 6,
    /// <summary>Synthesis material slots. See <see cref="SkillObjectItemEvolvingMaterials"/>.</summary>
    ItemEvolvingMaterials = 8,
    /// <summary>Random synthesis-effect replacement. See <see cref="SkillObjectEvolvingRerollOptions"/>.</summary>
    EvolvingRerollOptions = 9,
    /// <summary>Lunagem install options. See <see cref="SkillObjectSocketInstallOptions"/>.</summary>
    SocketInstallOptions = 10,
    /// <summary>Chosen awakening target. See <see cref="SkillObjectItemChangeMapping"/>.</summary>
    ItemChangeMapping = 26
}

public class SkillObject : PacketMarshaler
{
    public SkillObjectType Flag { get; set; } = SkillObjectType.None;

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write((byte)Flag);
        return stream;
    }

    /// <summary>
    /// Types this server can parse. The client models 30; reading one it does not know would consume
    /// the wrong number of bytes, so unknown types are dropped rather than guessed at.
    /// </summary>
    public static bool IsKnownType(int flagType) =>
        flagType is >= (int)SkillObjectType.Unk1 and <= (int)SkillObjectType.ItemGradeEnchantingSupport
            or (int)SkillObjectType.ItemEvolvingMaterials
            or (int)SkillObjectType.EvolvingRerollOptions
            or (int)SkillObjectType.SocketInstallOptions
            or (int)SkillObjectType.ItemChangeMapping;

    public static SkillObject GetByType(SkillObjectType flag)
    {
        SkillObject obj;
        switch (flag)
        {
            case SkillObjectType.Unk1: // TODO - Skills bound to portals
                obj = new SkillObjectUnk1();
                break;
            case SkillObjectType.Unk2: // TODO - Skills bound to home portals
                obj = new SkillObjectUnk2();
                break;
            case SkillObjectType.Unk3:
                obj = new SkillObjectUnk3();
                break;
            case SkillObjectType.Unk4:
                obj = new SkillObjectUnk4();
                break;
            case SkillObjectType.Unk5:
                obj = new SkillObjectUnk5();
                break;
            case SkillObjectType.ItemGradeEnchantingSupport:
                obj = new SkillObjectItemGradeEnchantingSupport();
                break;
            case SkillObjectType.ItemEvolvingMaterials:
                obj = new SkillObjectItemEvolvingMaterials();
                break;
            case SkillObjectType.EvolvingRerollOptions:
                obj = new SkillObjectEvolvingRerollOptions();
                break;
            case SkillObjectType.SocketInstallOptions:
                obj = new SkillObjectSocketInstallOptions();
                break;
            case SkillObjectType.ItemChangeMapping:
                obj = new SkillObjectItemChangeMapping();
                break;
            case SkillObjectType.None:
            default:
                obj = new SkillObject();
                break;
        }

        obj.Flag = flag;
        return obj;
    }
}

/// <summary>
/// AA10 r575 synthesis-effect replacement context (skill-object type 9).
/// </summary>
/// <remarks>
/// The client converts its one-based visual row to a zero-based physical modifier index before
/// writing the first <c>u32</c>. The second <c>u32</c> is zero for a random replacement or the exact
/// <c>item_rnd_attr_unit_modifier_groups.id</c> selected in the guaranteed-replacement window.
/// </remarks>
public sealed class SkillObjectEvolvingRerollOptions : SkillObject
{
    public uint ModifierIndex { get; set; }
    public uint ChangeToGroupId { get; set; }

    public override void Read(PacketStream stream)
    {
        ModifierIndex = stream.ReadUInt32();
        ChangeToGroupId = stream.ReadUInt32();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(ModifierIndex);
        stream.Write(ChangeToGroupId);
        return stream;
    }
}

/// <summary>
/// Gear Upgrade's Lunagem install context (skill-object type 10).
/// </summary>
/// <remarks>
/// r575 writes exactly six bytes before the common <c>inputDirection</c> byte:
/// <c>bool autoUseAaPoint</c>, <c>u32 count</c>, <c>bool continuous</c>. A zero count is the
/// client's representation of the default single install and is normalized by the executor.
/// </remarks>
public class SkillObjectSocketInstallOptions : SkillObject
{
    public bool AutoUseAaPoint { get; set; }
    public uint Count { get; set; }
    public bool Continuous { get; set; }

    public override void Read(PacketStream stream)
    {
        AutoUseAaPoint = stream.ReadBoolean();
        Count = stream.ReadUInt32();
        Continuous = stream.ReadBoolean();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(AutoUseAaPoint);
        stream.Write(Count);
        stream.Write(Continuous);
        return stream;
    }
}

public class SkillObjectUnk1 : SkillObject
{
    public byte Type { get; set; }
    public int Id { get; set; }
    public float X { get; set; }
    public float Y { get; set; }
    public float Z { get; set; }

    public override void Read(PacketStream stream)
    {
        Type = stream.ReadByte();
        Id = stream.ReadInt32();
        X = Helpers.ConvertLongX(stream.ReadInt64());
        Y = Helpers.ConvertLongX(stream.ReadInt64());
        Z = stream.ReadSingle();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(Type);
        stream.Write(Id);
        stream.Write(Helpers.ConvertLongX(X));
        stream.Write(Helpers.ConvertLongX(Y));
        stream.Write(Z);
        return stream;
    }
}

public class SkillObjectUnk2 : SkillObject
{
    public int Id { get; set; }
    public string Name { get; set; }

    public override void Read(PacketStream stream)
    {
        Id = stream.ReadInt32();
        Name = stream.ReadString();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(Id);
        stream.Write(Name);
        return stream;
    }
}

public class SkillObjectUnk3 : SkillObject
{
    public string Msg { get; set; }

    public override void Read(PacketStream stream)
    {
        Msg = stream.ReadString();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(Msg);
        return stream;
    }
}

public class SkillObjectUnk4 : SkillObject
{
    public float X { get; set; }
    public float Y { get; set; }
    public float Z { get; set; }

    public override void Read(PacketStream stream)
    {
        X = Helpers.ConvertLongX(stream.ReadInt64());
        Y = Helpers.ConvertLongY(stream.ReadInt64());
        Z = stream.ReadSingle();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(Helpers.ConvertLongX(X));
        stream.Write(Helpers.ConvertLongY(Y));
        stream.Write(Z);
        return stream;
    }
}

public class SkillObjectUnk5 : SkillObject
{
    public int Step { get; set; }

    public override void Read(PacketStream stream)
    {
        Step = stream.ReadInt32();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(Step);
        return stream;
    }
}

/// <summary>
/// AA10 r575 skill-object type 6. The Gear Upgrade client sends exactly a support item id and the
/// AA-points payment choice. Type 7 and the historical string-shaped type 6 are not part of this
/// Temper wire contract.
/// </summary>
public class SkillObjectItemGradeEnchantingSupport : SkillObject
{
    public ulong SupportItemId { get; set; }
    public bool AutoUseAaPoint { get; set; }

    public override void Read(PacketStream stream)
    {
        SupportItemId = stream.ReadUInt64();
        AutoUseAaPoint = stream.ReadBoolean();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(SupportItemId);
        stream.Write(AutoUseAaPoint);
        return stream;
    }
}

/// <summary>
/// The synthesis window's material slots, sent with the item synthesis skill.
/// </summary>
/// <remarks>
/// <para>Schema:</para>
/// <code>
/// u16  byteLength      // length of the id array in bytes, not a count
/// u64  materialItemId[byteLength / 8]
/// bool autoUseAaPoint  // pay the fee from AA points instead of coin
/// </code>
/// <para>
/// <c>byteLength</c> is declared by the sender and is authoritative for how many ids follow, so
/// <see cref="MaterialSlots"/> is only the default the window offers. Validation rules:
/// a length that is not a whole multiple of 8 leaves a partial id, whose bytes are consumed and
/// discarded so the fields after this object stay aligned; unused slots are sent as 0 and are not
/// materials. A caller must therefore take <see cref="UsedMaterialItemIds"/> rather than assume the
/// array is full or of a fixed size.
/// </para>
/// <para>
/// The trailing <c>inputDirection</c> byte is common to every skill-object type and belongs to
/// CSStartSkillPacket, which reads it after this body.
/// </para>
/// </remarks>
public class SkillObjectItemEvolvingMaterials : SkillObject
{
    /// <summary>Slots the client offers. The wire length is authoritative; this is only the default.</summary>
    public const int MaterialSlots = 6;

    public ulong[] MaterialItemIds { get; set; } = new ulong[MaterialSlots];
    public bool AutoUseAaPoint { get; set; }
    public ushort DeclaredByteLength { get; private set; }
    public bool HasMalformedLength => DeclaredByteLength % sizeof(ulong) != 0;
    public bool HasTooManySlots => DeclaredByteLength / sizeof(ulong) > MaterialSlots;
    public bool HasValidWireShape => !HasMalformedLength && !HasTooManySlots;

    /// <summary>The filled slots, in the order the client listed them.</summary>
    public IEnumerable<ulong> UsedMaterialItemIds => MaterialItemIds.Where(id => id != 0);

    public override void Read(PacketStream stream)
    {
        DeclaredByteLength = stream.ReadUInt16();
        var count = DeclaredByteLength / sizeof(ulong);
        MaterialItemIds = new ulong[Math.Min(count, MaterialSlots)];
        for (var i = 0; i < count; i++)
        {
            var id = stream.ReadUInt64();
            if (i < MaterialItemIds.Length)
                MaterialItemIds[i] = id;
        }

        // A length that is not a whole number of ids would leave the stream mid-field; drop the
        // remainder rather than desyncing everything after the skill object.
        for (var i = 0; i < DeclaredByteLength % sizeof(ulong); i++)
            _ = stream.ReadByte();

        AutoUseAaPoint = stream.ReadBoolean();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        var ids = MaterialItemIds ?? [];
        if (ids.Length > MaterialSlots)
            throw new InvalidOperationException($"Synthesis accepts at most {MaterialSlots} material slots.");
        stream.Write((ushort)(ids.Length * sizeof(ulong)));
        foreach (var id in ids)
            stream.Write(id);
        stream.Write(AutoUseAaPoint);
        return stream;
    }
}

/// <summary>
/// The awakening ("각성") target the player picked, sent with an awakening scroll's use skill.
/// </summary>
/// <remarks>
/// <para>Schema: a single <c>u32 mappingId</c>.</para>
/// <para>
/// It names the <c>item_change_mappings</c> row the player chose, which matters when a group offers
/// more than one target for the same source item and grade (<c>selectable</c>). The server treats it
/// as a request, not an instruction: the awakening effect honours it only when the row really belongs
/// to the group named by the skill and matches the target's item and grade, and otherwise falls back
/// to the group's own resolution.
/// </para>
/// </remarks>
public class SkillObjectItemChangeMapping : SkillObject
{
    public uint MappingId { get; set; }

    public override void Read(PacketStream stream)
    {
        MappingId = stream.ReadUInt32();
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);
        stream.Write(MappingId);
        return stream;
    }
}
