using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Consolidated AA8 socketing response (x2game.dll, opcode 0x279).
    /// Operation 0/1 is consumed as remove/install by FUN_39301ac0.
    /// </summary>
    public sealed class SCSocketingResultPacket : GamePacket
    {
        private readonly byte _result;
        private readonly ulong _itemId;
        private readonly uint _itemTemplateId;
        private readonly byte _operation;
        private readonly bool _success;

        public SCSocketingResultPacket(
            byte result,
            ulong itemId,
            uint itemTemplateId,
            byte operation,
            bool success)
            : base(SCOffsets.SCSocketingResultPacket, 5)
        {
            _result = result;
            _itemId = itemId;
            _itemTemplateId = itemTemplateId;
            _operation = operation;
            _success = success;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_result);
            stream.Write(_itemId);
            stream.Write(_itemTemplateId);
            stream.Write(_operation);
            stream.Write(_success);
            return stream;
        }
    }
}
