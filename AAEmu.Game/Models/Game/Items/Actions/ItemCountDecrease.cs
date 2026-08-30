using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions;

/// <summary>
/// Subtracts a positive amount from an existing AA10 r575 item stack.
/// </summary>
/// <remarks>
/// The r575 action-5 codec (<c>FUN_39b50ab0</c>) carries a signed 32-bit amount. Its apply consumer
/// (<c>FUN_39b56cb0</c>) adds that signed value to the addressed stack, while the notification path
/// (<c>FUN_398d50a0</c> -> <c>FUN_398e2ea0</c>) preserves the sign and renders a removal for negative
/// deltas. Full-stack deletion continues to use <see cref="ItemRemoveSlot"/> and force-removes.
/// </remarks>
public sealed class ItemCountDecrease : ItemTask
{
    private readonly Item _item;
    private readonly int _amount;

    public ItemCountDecrease(Item item, int amount)
    {
        ArgumentNullException.ThrowIfNull(item);
        if (amount <= 0)
            throw new ArgumentOutOfRangeException(nameof(amount), amount, "A stack decrease must be positive.");

        _item = item;
        _amount = amount;
        _type = ItemAction.Create;
    }

    public override PacketStream Write(PacketStream stream)
    {
        base.Write(stream);

        stream.Write((byte)_item.SlotType);
        stream.Write((byte)_item.Slot);
        stream.Write(_item.Id);
        stream.Write(-_amount);
        stream.Write(_item.TemplateId);

        return stream;
    }
}
