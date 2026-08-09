using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Char
{
    /// <summary>
    /// Exact AA8 wire layout used by an individual C2G action-slot update.
    /// </summary>
    public static class ActionSlotWireCodec
    {
        public static bool TryReadUpdate(
            PacketStream stream,
            out byte slot,
            out ActionSlotType type,
            out ulong actionId,
            out string error)
        {
            slot = 0;
            type = ActionSlotType.None;
            actionId = 0;
            error = string.Empty;
            if (stream == null || stream.LeftBytes < 2)
            {
                error = $"payload has only {stream?.LeftBytes ?? 0} bytes";
                return false;
            }

            slot = stream.ReadByte();
            type = (ActionSlotType)stream.ReadByte();
            var expectedReferenceBytes = 0;
            switch (type)
            {
                case ActionSlotType.None:
                    break;
                case ActionSlotType.ItemType:
                case ActionSlotType.Spell:
                case ActionSlotType.RidePetSpell:
                case ActionSlotType.BattlePetSpell:
                    expectedReferenceBytes = sizeof(uint);
                    break;
                case ActionSlotType.ItemId:
                    expectedReferenceBytes = sizeof(ulong);
                    break;
                default:
                    error = $"unsupported action type {(byte)type}";
                    return false;
            }

            if (stream.LeftBytes != expectedReferenceBytes)
            {
                error =
                    $"payload reference has {stream.LeftBytes} bytes; expected {expectedReferenceBytes}";
                return false;
            }

            if (expectedReferenceBytes == sizeof(uint))
                actionId = stream.ReadUInt32();
            else if (expectedReferenceBytes == sizeof(ulong))
                actionId = stream.ReadUInt64();
            return true;
        }
    }
}
