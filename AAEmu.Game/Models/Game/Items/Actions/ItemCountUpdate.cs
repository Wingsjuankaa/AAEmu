using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions;

public class ItemCountUpdate : ItemTask
{
    private readonly Item _item;

    /// <summary>
    /// Re-states the authoritative final stack size of an existing item.
    /// </summary>
    /// <param name="item">Item whose count has already been changed</param>
    /// <param name="count">
    /// Signed delta that was applied. Kept for call-site clarity only — the wire carries the resulting
    /// stack size, not the delta.
    /// </param>
    /// <remarks>
    /// Always Take (action 6): slot followed by a full item body whose stackSize is the new count. This
    /// remains the conservative synchronization path for moves and merges.
    /// <para>
    /// Acquisition and consumption notifications must not use this full snapshot: r575 reports its final
    /// stackSize as an acquired amount. Those paths use <see cref="ItemCountIncrease"/> and
    /// <see cref="ItemCountDecrease"/>, whose signed action-5 delta is applied to the existing stack and
    /// rendered with the correct direction.
    /// </para>
    /// <para>
    /// Seize remains reserved for deleting a whole stack. AddStack (action 4) is templateId + amount with
    /// no slot or item id, so it cannot address a particular stack.
    /// </para>
    /// </remarks>
    public ItemCountUpdate(Item item, int count)
    {
        _ = count;
        _item = item;
        _type = ItemAction.Take;
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);

        stream.Write((byte)_item.SlotType);
        stream.Write((byte)_item.Slot);
        WriteDetails(stream, _item);

        return stream;
    }
}
