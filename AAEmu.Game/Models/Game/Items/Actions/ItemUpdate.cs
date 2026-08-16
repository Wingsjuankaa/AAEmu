using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions;

/// <summary>
/// UpdateDetail item task (action 10).
/// </summary>
/// <remarks>
/// AA10 r575 schema: <c>u8 slotType, u8 slot, u64 itemId</c>, followed by a length-prefixed
/// 128-byte internal detail union.
/// <para>
/// <b>Do not use the compact <see cref="Item.WriteDetails"/> payload here.</b> UpdateDetail copies this
/// distinct fixed-layout union directly into the client's live item. Sending the compact payload
/// replaces it with an invalid/black snapshot.
/// </para>
/// </remarks>
public class ItemUpdate : ItemTask
{
    private readonly Item _item;

    public ItemUpdate(Item item)
    {
        _type = ItemAction.UpdateDetail;
        _item = item;
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);

        stream.Write((byte)_item.SlotType);
        stream.Write((byte)_item.Slot);

        stream.Write(_item.Id);
        stream.Write((short)128);
        _item.WriteUpdateDetailBlock(stream);
        return stream;
    }
}
