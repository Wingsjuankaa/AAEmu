using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Kakao 8.0 evolving random-attribute replacement result.
    /// PTR_FUN_39cfa248 / FUN_399a1f80 confirms the wire layout.
    /// </summary>
    public sealed class SCEvolvingReRollResultPacket : GamePacket
    {
        private readonly ulong _itemId;
        private readonly byte _modifierIndex;
        private readonly bool _changed;
        private readonly EvolvingModifierResult _before;
        private readonly EvolvingModifierResult _after;

        public SCEvolvingReRollResultPacket(
            ulong itemId,
            byte modifierIndex,
            bool changed,
            EvolvingModifierResult before,
            EvolvingModifierResult after)
            : base(SCOffsets.SCEvolvingReRollResultPacket, 5)
        {
            _itemId = itemId;
            _modifierIndex = modifierIndex;
            _changed = changed;
            _before = before;
            _after = after;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_itemId);
            stream.Write(_modifierIndex);
            stream.Write(_changed);
            WriteModifier(stream, _before);
            WriteModifier(stream, _after);
            return stream;
        }

        private static void WriteModifier(
            PacketStream stream,
            EvolvingModifierResult modifier)
        {
            stream.Write(modifier.UnitAttributeId);
            stream.Write(modifier.UnitModifierTypeId);
            stream.Write(modifier.Value);
        }
    }
}
