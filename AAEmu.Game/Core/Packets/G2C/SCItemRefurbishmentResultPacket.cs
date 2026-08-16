using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// AA10 r575 Temper result. x2game.dll's native packet serializer writes a byte result,
/// ItemLink, a reserved uint32 and the before/after scale ids, in that order.
/// </summary>
public sealed class SCItemRefurbishmentResultPacket : GamePacket
{
    private readonly ItemRefurbishmentResult _result;
    private readonly Item _item;
    private readonly ushort _beforeScale;
    private readonly ushort _afterScale;

    public SCItemRefurbishmentResultPacket(ItemRefurbishmentResult result, Item item,
        ushort beforeScale, ushort afterScale)
        : base(SCOffsets.SCItemRefurbishmentResultPacket, 5)
    {
        _result = result;
        _item = item;
        _beforeScale = beforeScale;
        _afterScale = afterScale;
    }

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write((byte)_result);
        stream.Write(_item);
        stream.Write(0u); // client-reserved field at native packet offset 0xE8
        stream.Write(_beforeScale);
        stream.Write(_afterScale);
        return stream;
    }
}
