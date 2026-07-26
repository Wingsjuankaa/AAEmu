using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Char
{
    public static class CharacterSelectionWireCodec
    {
        public const int PayloadSize = sizeof(uint) + sizeof(byte);

        public static bool TryRead(
            PacketStream stream,
            out uint characterId,
            out bool skipClientDriven,
            out string error)
        {
            characterId = 0;
            skipClientDriven = false;
            error = null;

            if (stream == null || stream.LeftBytes != PayloadSize)
            {
                error =
                    $"AA8 character selection requires exactly {PayloadSize} payload bytes";
                return false;
            }

            characterId = stream.ReadUInt32();
            var rawSkipClientDriven = stream.ReadByte();
            if (rawSkipClientDriven > 1)
            {
                error = $"AA8 character selection has invalid boolean value {rawSkipClientDriven}";
                return false;
            }

            skipClientDriven = rawSkipClientDriven == 1;
            return true;
        }
    }
}
