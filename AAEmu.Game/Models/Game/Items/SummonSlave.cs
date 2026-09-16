using System.Numerics;
using AAEmu.Commons.Network;
using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Items.Templates;

namespace AAEmu.Game.Models.Game.Items;

public class SummonSlave : Item
{
    private DateTime _repairStartTime;
    public override ItemDetailType DetailType => ItemDetailType.Slave;
    // r575 Item+0x21: u32 dbId, byte destroyed, i64 repair time, i64 x/y, four trailing bytes.
    // Native consumers: RVA 0x656080 and 0x656620. The detail discriminator is emitted by Item.
    public override uint DetailBytesLength => 33;
    private const uint PersistentFormat = 0x30314C53; // "SL10", storage only
    public uint DetailTail { get; set; }
    public uint SlaveDbId { get; set; }
    public byte IsDestroyed { get; set; }

    public DateTime RepairStartTime
    {
        get => _repairStartTime;
        set
        {
            _repairStartTime = value;
            if (value > DateTime.MinValue)
                IsDestroyed = 0;
        }
    }

    public Vector3 SummonLocation { get; set; }

    public SummonSlave()
    {
        //
    }

    public SummonSlave(ulong id, ItemTemplate template, int count) : base(id, template, count)
    {
        //
    }

    public override void ReadDetails(PacketStream stream)
    {
        if (stream.LeftBytes < DetailBytesLength)
            return;
        SlaveDbId = stream.ReadUInt32();
        IsDestroyed = stream.ReadByte();
        _repairStartTime = ReadRepairTime(stream.ReadInt64());
        SummonLocation = new Vector3(Helpers.ConvertLongX(stream.ReadInt64()),
            Helpers.ConvertLongY(stream.ReadInt64()), 0);
        DetailTail = stream.ReadUInt32();
    }

    public override void WriteDetails(PacketStream stream)
    {
        stream.Write(SlaveDbId);
        stream.Write(IsDestroyed);
        stream.Write(RepairStartTime);
        stream.Write(Helpers.ConvertLongX(SummonLocation.X));
        stream.Write(Helpers.ConvertLongY(SummonLocation.Y));
        stream.Write(DetailTail);
    }

    public override void WritePersistentDetails(PacketStream stream)
    {
        stream.Write(PersistentFormat);
        WriteDetails(stream);
    }

    public override void ReadPersistentDetails(PacketStream stream)
    {
        var length = stream.LeftBytes;
        if (length == 0)
            return;
        if (length != 33 && length != 37)
            throw new InvalidDataException($"Unexpected slave detail length {length} for item {Id}");

        var prefix = stream.ReadUInt32();
        if (length == 37 && prefix == PersistentFormat)
        {
            ReadDetails(stream);
            return;
        }

        // Old AAEmu persisted [redundant type byte, bc dbId, destroyed, time32/64, zeros].
        // Recover that ID exactly once; never guess based on the low byte of a native ID.
        SlaveDbId = prefix >> 8;
        IsDestroyed = stream.ReadByte();
        _repairStartTime = ReadRepairTime(length == 37 ? stream.ReadInt64() : stream.ReadInt32());
        _ = stream.ReadBytes(24);
        IsDirty = true;
    }

    private static DateTime ReadRepairTime(long seconds) =>
        seconds == 0 ? DateTime.MinValue : DateTimeOffset.FromUnixTimeSeconds(seconds).UtcDateTime;

    public override void OnManuallyDestroyingItem()
    {
        var owner = WorldManager.Instance.GetCharacterById((uint)OwnerId);
        if (owner == null)
            return;

        if (!owner.ParentWorld.SlaveManager.OnDeleteSlaveItem(this))
            Logger.Warn($"Failed to delete Slave attached to Item Id: {Id}, Type: {TemplateId}");
    }

    public override bool CanDestroy()
    {
        if (!base.CanDestroy())
            return false;

        // TODO: Always allow expired items to be removed regardless if summoned or not 
        var owner = WorldManager.Instance.GetCharacterById((uint)OwnerId);
        if (owner != null)
        {
            var checkSlave = owner.ParentWorld.SlaveManager.GetActiveSlaveByOwnerObjId(owner.ObjId);
            if (checkSlave?.Id == SlaveDbId)
            {
                owner.SendErrorMessage(ErrorMessageType.SlaveSpawnItemLocked);
                return false;
            }
        }

        return true;
    }
}
