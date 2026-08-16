using System.Buffers.Binary;

using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items;

public class EquipItem : Item
{
    public override ItemDetailType DetailType => ItemDetailType.Equipment;

    public byte Durability { get; set; }
    private ushort _scaledA;

    /// <summary>
    /// Native r575 Temper descriptor stored at equipment-detail offset 0x3C. It is an
    /// <c>enchant_scale_ratios.id</c>, not an enchanting-item template id.
    /// </summary>
    public ushort ScaledA
    {
        get => _scaledA;
        set
        {
            _scaledA = value;
            IsDirty = true;
        }
    }

    /// <summary>Compatibility alias for code written before offset 0x3C was identified as ScaledA.</summary>
    public uint RuneId
    {
        get => _scaledA;
        set => ScaledA = checked((ushort)value);
    }
    public ushort TemperPhysical { get; set; }
    public ushort TemperMagical { get; set; }

    public ushort EvolveChance { get; set; }
    public DateTime ChargeProcTime { get; set; } = DateTime.MinValue;
    public byte MappingFailBonus { get; set; }
    public byte ElementLevel { get; set; }
    /// <summary>
    /// The equipment detail's value block, serialized and persisted as a whole by the pish/pisc codec.
    /// </summary>
    /// <remarks>
    /// Its length and the position of every value are part of the item detail contract, shared by the
    /// network body and the stored <c>items.details</c> blob, so entries are addressed through the
    /// named indices below and the block is always <see cref="GemDataSlots"/> long. Values this server
    /// does not yet interpret still round-trip unchanged, which is what keeps a detail written by an
    /// older build readable. Assigning the array does not by itself mark the item dirty; the accessors
    /// below do that.
    /// </remarks>
    public uint[] GemData { get; set; }

    /// <summary>Length of <see cref="GemData"/>. Fixed by the item detail contract.</summary>
    public const int GemDataSlots = 18;

    /// <summary>
    /// Synthesis ("Item Growth") experience accumulated at the current grade.
    /// </summary>
    /// <remarks>
    /// Held in <see cref="GemData"/> at <see cref="EvolvingExpGemDataIndex"/>. Never negative: a lower
    /// value is clamped to zero rather than wrapping, since the block is unsigned. Writing it marks the
    /// item dirty, without which the value reaches the client and is then lost at the next persist pass.
    /// </remarks>
    public int EvolvingExp
    {
        get => (int)(GemData is { Length: > EvolvingExpGemDataIndex } ? GemData[EvolvingExpGemDataIndex] : 0u);
        set
        {
            var gemData = GemData ?? new uint[GemDataSlots];
            if (gemData.Length < GemDataSlots)
                Array.Resize(ref gemData, GemDataSlots);
            gemData[EvolvingExpGemDataIndex] = (uint)Math.Max(0, value);
            GemData = gemData;
            IsDirty = true;
        }
    }

    /// <summary>Index of the synthesis experience within <see cref="GemData"/>.</summary>
    private const int EvolvingExpGemDataIndex = 3;

    /// <summary>First Lunagem entry in the native r575 equipment value block.</summary>
    public const int NativeSocketStartIndex = 4;

    /// <summary>Number of contiguous Lunagem entries exposed by the r575 client.</summary>
    public const int NativeSocketCapacity = 9;

    /// <summary>The installed Lunagem template ids, including empty entries.</summary>
    public IEnumerable<uint> NativeSocketItemIds
    {
        get
        {
            for (var index = 0; index < NativeSocketCapacity; index++)
                yield return GemData is { Length: >= GemDataSlots }
                    ? GemData[NativeSocketStartIndex + index]
                    : 0u;
        }
    }

    public int OccupiedNativeSocketCount => NativeSocketItemIds.Count(itemId => itemId != 0);

    public bool SetNativeSocket(int socketIndex, uint itemTemplateId)
    {
        if (socketIndex is < 0 or >= NativeSocketCapacity)
            return false;

        var gemData = GemData ?? new uint[GemDataSlots];
        if (gemData.Length < GemDataSlots)
            Array.Resize(ref gemData, GemDataSlots);
        gemData[NativeSocketStartIndex + socketIndex] = itemTemplateId;
        GemData = gemData;
        IsDirty = true;
        return true;
    }

    public bool TryGetFirstEmptyNativeSocket(int maximumSockets, out int socketIndex)
    {
        var limit = Math.Clamp(maximumSockets, 0, NativeSocketCapacity);
        for (var index = 0; index < limit; index++)
        {
            if (GemData is { Length: >= GemDataSlots } &&
                GemData[NativeSocketStartIndex + index] != 0)
                continue;

            socketIndex = index;
            return true;
        }

        socketIndex = -1;
        return false;
    }

    /// <summary>How many synthesis effects an item can carry.</summary>
    public const int RndAttrSlots = 5;

    /// <summary>Index of the first synthesis effect within <see cref="GemData"/>; they are contiguous.</summary>
    private const int RndAttrFirstGemDataIndex = 13;

    /// <summary>
    /// The "Synthesis Effect" lines this item carries, as
    /// <c>item_rnd_attr_unit_modifier_groups</c> ids.
    /// </summary>
    /// <remarks>
    /// Held in <see cref="GemData"/> at <see cref="RndAttrFirstGemDataIndex"/> and the
    /// <see cref="RndAttrSlots"/> - 1 entries after it. Only the group is stored, never a magnitude:
    /// the value of an effect is looked up from <c>item_rnd_attr_unit_modifiers</c> for that group at
    /// the item's current grade, which is why the same effect is worth more as the item is synthesized.
    /// Reading yields only the occupied slots; writing takes at most <see cref="RndAttrSlots"/> ids and
    /// zeroes the rest, so assigning an empty sequence clears them all.
    /// </remarks>
    public IEnumerable<uint> RndAttrGroupIds
    {
        get
        {
            for (var i = 0; i < RndAttrSlots; i++)
            {
                var id = GemData is { Length: >= GemDataSlots } ? GemData[RndAttrFirstGemDataIndex + i] : 0u;
                if (id != 0)
                    yield return id;
            }
        }
        set
        {
            var gemData = GemData ?? new uint[GemDataSlots];
            if (gemData.Length < GemDataSlots)
                Array.Resize(ref gemData, GemDataSlots);

            var ids = (value ?? []).Take(RndAttrSlots).ToArray();
            for (var i = 0; i < RndAttrSlots; i++)
                gemData[RndAttrFirstGemDataIndex + i] = i < ids.Length ? ids[i] : 0u;

            GemData = gemData;
            IsDirty = true;
        }
    }

    public virtual int Str => 0;
    public virtual int Dex => 0;
    public virtual int Sta => 0;
    public virtual int Int => 0;
    public virtual int Spi => 0;
    public virtual byte MaxDurability => 0;

    /// <summary>
    /// The item ID of the dye pot that was used on the equipment.
    /// </summary>
    public uint DyeItemId { get; set; }

    public int RepairCost
    {
        get
        {
            var template = (EquipItemTemplate)Template;
            var grade = ItemManager.Instance.GetGradeTemplate(Grade);
            var cost = ItemManager.Instance.GetDurabilityRepairCostFactor() * 0.0099999998f *
                       (1f - Durability * 1f / MaxDurability) * template.Price;
            cost = cost * grade.RefundMultiplier * 0.0099999998f;
            cost = (float)Math.Ceiling(cost);
            if (cost < 0 || cost < int.MinValue || cost > int.MaxValue)
                cost = 0;
            return (int)cost;
        }
    }

    public EquipItem()
    {
        GemData = new uint[GemDataSlots];
    }

    public EquipItem(ulong id, ItemTemplate template, int count) : base(id, template, count)
    {
        GemData = new uint[GemDataSlots];
        // 10.0.2.13: DefaultDyeItemId removed; DyeItemId defaults to 0 (was always 0 via mock)
    }

    public override void Read(PacketStream stream)
    {
        TemplateId = stream.ReadUInt32();

        if (TemplateId == 0)
            return;

        Id = stream.ReadUInt64();
        Grade = stream.ReadByte();
        ItemFlags = (ItemFlag)stream.ReadByte();
        Count = stream.ReadInt32();
        var detailType = stream.ReadByte();
        ReadDetails(stream);
        CreateTime = stream.ReadDateTime();
        LifespanMins = stream.ReadInt32();
        MadeUnitId = (uint)stream.ReadUInt64(); // v10: madeUnitId is 8 bytes on the wire
        WorldId = stream.ReadByte();
        UnsecureTime = stream.ReadDateTime();
        UnpackTime = stream.ReadDateTime();
        ChargeUseSkillTime = stream.ReadDateTime(); // v10: new trailing field
    }

    // The same body serves the network detail and the persisted items.details blob, so a change here
    // changes the stored format too. GemData is variable length on the wire; GemDataSlots is what this
    // server reads and writes.
    public override void ReadDetails(PacketStream stream)
    {
        Durability = stream.ReadByte();
        ChargeCount = stream.ReadUInt16(); // chargeCount is u16, not i32
        ChargeStartTime = stream.ReadDateTime();
        _scaledA = stream.ReadUInt16();
        EvolveChance = stream.ReadUInt16();
        ChargeProcTime = stream.ReadDateTime();
        MappingFailBonus = stream.ReadByte();
        ElementLevel = stream.ReadByte();
        GemData = stream.ReadPisc(GemDataSlots);
    }

    public override void WriteDetails(PacketStream stream)
    {
        stream.Write(Durability);          // durability u8
        stream.Write((ushort)ChargeCount); // chargeCount u16
        stream.Write(ChargeStartTime);     // chargeTime i64
        stream.Write(ScaledA);             // scaledA u16 (Temper ratio id)
        stream.Write(EvolveChance);        // evolveChance u16
        stream.Write(ChargeProcTime);      // chargeProcTime i64
        stream.Write(MappingFailBonus);    // mappingFailBonus u8
        stream.Write(ElementLevel);        // elementLevel u8
        // Then the 18-value equipment block. Native r575 uses [4..12] for its nine Lunagem slots.
        // ImageItemTemplateId must occupy GemData[0] on the wire.
        var gemData = GemData ?? new uint[GemDataSlots];
        if (gemData.Length < GemDataSlots)
            Array.Resize(ref gemData, GemDataSlots);
        gemData[0] = ImageItemTemplateId;
        stream.WritePisc(gemData);
    }

    /// <summary>
    /// Writes the AA10 r575 internal equipment-detail union used exclusively by
    /// ItemAction.UpdateDetail.
    /// </summary>
    /// <remarks>
    /// Proven from x2game.dll FUN_39a3ccd0 (compact detail codec) and FUN_39b57130
    /// (UpdateDetail applies memcpy(item + 0x20, detail, 0x80)). The 18 PISC values are
    /// deliberately scattered in this native layout and cannot be replaced with WriteDetails().
    /// </remarks>
    public override void WriteUpdateDetailBlock(PacketStream stream)
    {
        const int blockSize = 0x80;
        var block = new byte[blockSize];
        var values = GemData ?? new uint[GemDataSlots];
        if (values.Length < GemDataSlots)
            Array.Resize(ref values, GemDataSlots);
        values[0] = ImageItemTemplateId;

        block[0] = (byte)DetailType;
        WriteUInt32(block, 0x01, values[0]);
        block[0x05] = Durability;
        BinaryPrimitives.WriteUInt16LittleEndian(block.AsSpan(0x06, sizeof(ushort)), (ushort)ChargeCount);
        WriteUInt32(block, 0x08, values[1]);
        WriteInt64(block, 0x0C, Helpers.UnixTime(ChargeStartTime));
        WriteUInt32(block, 0x14, values[2]);

        for (var index = 0; index < 9; index++)
            WriteUInt32(block, 0x18 + index * sizeof(uint), values[index + 4]);

        BinaryPrimitives.WriteUInt16LittleEndian(block.AsSpan(0x3C, sizeof(ushort)), ScaledA);
        BinaryPrimitives.WriteUInt16LittleEndian(block.AsSpan(0x3E, sizeof(ushort)), EvolveChance);
        WriteUInt32(block, 0x40, values[3]);

        for (var index = 0; index < 5; index++)
            WriteUInt32(block, 0x44 + index * sizeof(uint), values[index + 13]);

        WriteInt64(block, 0x58, Helpers.UnixTime(ChargeProcTime));
        block[0x60] = MappingFailBonus;
        block[0x61] = ElementLevel;
        stream.Write(block, false);
    }

    private static void WriteUInt32(byte[] target, int offset, uint value) =>
        BinaryPrimitives.WriteUInt32LittleEndian(target.AsSpan(offset, sizeof(uint)), value);

    private static void WriteInt64(byte[] target, int offset, long value) =>
        BinaryPrimitives.WriteInt64LittleEndian(target.AsSpan(offset, sizeof(long)), value);
}
