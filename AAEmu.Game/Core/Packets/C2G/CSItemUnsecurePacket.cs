using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSItemUnsecurePacket() : GamePacket(CSOffsets.CSItemUnsecurePacket, 1)
{
    public SlotType SlotType { get; private set; }
    public byte Slot { get; private set; }
    public ulong ItemId { get; private set; }

    public override void Read(PacketStream stream)
    {
        SlotType = (SlotType)stream.ReadByte();
        Slot = stream.ReadByte();
        ItemId = stream.ReadUInt64();
    }

    public override void Execute() =>
        ItemSecurityService.Instance.UnlockItem(Connection?.ActiveChar, SlotType, Slot, ItemId);
}
