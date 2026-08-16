using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Pushes one item's detail blob to the client, opcode 0xBE.
/// </summary>
/// <remarks>
/// <para>Schema:</para>
/// <code>
/// u64 id          // item id
/// u8  slotType
/// u8  slot
/// detail          // the item detail exactly as the full item body carries it, leading detailType
///                 // byte included; written raw, with no length prefix and no padding
/// </code>
/// <para>
/// This publishes the compact item detail directly to the live item. It is not interchangeable with
/// the <c>UpdateDetail</c> item task: r575 decodes that task as a separate fixed 128-byte internal
/// union. Some native transactions use both views, so callers must select them from client evidence
/// instead of putting this compact payload inside <c>ItemUpdate</c>. Because the detail here is
/// written raw, its field order is the contract: a change to the detail serializer changes this
/// packet too.
/// </para>
/// </remarks>
public class SCItemDetailUpdatedPacket(Item item) : GamePacket(SCOffsets.SCItemDetailUpdatedPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(item.Id);
        stream.Write((byte)item.SlotType);
        stream.Write((byte)item.Slot);
        stream.Write((byte)item.DetailType);
        item.WriteDetails(stream);
        return stream;
    }
}
