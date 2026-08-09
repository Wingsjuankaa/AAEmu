using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// AA8 opcode 0x0B1.
    ///
    /// x2game FUN_399a1d90 confirms the wire layout:
    /// byte result, ItemLink item, uint32 clientReserved,
    /// uint16 beforeScale, uint16 afterScale.
    ///
    /// FUN_39302650 consumes the result, item link and both scale values.
    /// The intermediate uint32 is present on the wire but is not exposed to
    /// ITEM_REFURBISHMENT_RESULT, so the server writes its canonical value 0.
    /// </summary>
    public sealed class SCItemRefurbishmentResultPacket : GamePacket
    {
        private readonly ItemRefurbishmentResult _result;
        private readonly Item _item;
        private readonly ushort _beforeScale;
        private readonly ushort _afterScale;

        public SCItemRefurbishmentResultPacket(
            ItemRefurbishmentResult result,
            Item item,
            ushort beforeScale,
            ushort afterScale)
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
            stream.Write(0u); // AA8 client-reserved field at packet offset 0xE0.
            stream.Write(_beforeScale);
            stream.Write(_afterScale);
            return stream;
        }
    }
}
