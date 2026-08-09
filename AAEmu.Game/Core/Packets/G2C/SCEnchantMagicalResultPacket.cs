using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// AA8 magical enchanting response (x2game.dll reader FUN_39988dc0).
    /// </summary>
    public sealed class SCEnchantMagicalResultPacket : GamePacket
    {
        private readonly bool _result;
        private readonly ulong _itemId;
        private readonly uint _itemTemplateId;

        public SCEnchantMagicalResultPacket(bool result, ulong itemId, uint itemTemplateId)
            : base(SCOffsets.SCEnchantMagicalResultPacket, 5)
        {
            _result = result;
            _itemId = itemId;
            _itemTemplateId = itemTemplateId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_result);
            stream.Write(_itemId);
            stream.Write(_itemTemplateId);
            return stream;
        }
    }
}
