using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Char
{
    public static class CharacterListHandshakeWireCodec
    {
        public const int ReuseKeysPayloadSize = sizeof(uint);

        public static bool TryReadReuseKeys(PacketStream stream, out string error)
        {
            error = null;
            if (stream == null || stream.LeftBytes != ReuseKeysPayloadSize)
            {
                error =
                    $"AA8 in-session character-list handshake requires exactly {ReuseKeysPayloadSize} payload bytes";
                return false;
            }

            var reuseKeysSentinel = stream.ReadUInt32();
            if (reuseKeysSentinel != 0)
            {
                error =
                    $"AA8 in-session character-list handshake has invalid sentinel {reuseKeysSentinel}";
                return false;
            }

            return true;
        }
    }
}
