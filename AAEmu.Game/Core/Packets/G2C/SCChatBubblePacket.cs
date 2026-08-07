using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCChatBubblePacket : GamePacket
    {
        private readonly uint _objId;
        private readonly byte _kind;
        private readonly byte _payloadKind;
        private readonly uint _bubbleId;
        private readonly string _text;

        public SCChatBubblePacket(uint objId, byte kind, byte payloadKind, uint bubbleId, string text)
            : base(SCOffsets.SCChatBubblePacket, 1)
        {
            _objId = objId;
            _kind = kind;
            _payloadKind = payloadKind;
            _bubbleId = bubbleId;
            _text = text ?? string.Empty;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);
            stream.Write(_kind);
            stream.Write(_payloadKind);
            if (_payloadKind == 1)
                stream.Write(_text);
            else
                stream.Write(_bubbleId);
            return stream;
        }
    }
}
