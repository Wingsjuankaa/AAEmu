using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 result for replacing one synthesis-effect line (opcode 0xCE).</summary>
/// <remarks>
/// Exact native body: <c>u64 itemId, u8 modifierIndex, bool changed,</c> followed by the before and
/// after modifiers, each encoded as <c>u16 unitAttributeId, u8 unitModifierTypeId, i32 value</c>.
/// </remarks>
public sealed class SCItemReRollEvolvingResultPacket : GamePacket
{
    public readonly record struct EvolvingModifier(ushort UnitAttributeId, byte UnitModifierTypeId, int Value);

    private readonly ulong _itemId;
    private readonly byte _modifierIndex;
    private readonly bool _changed;
    private readonly EvolvingModifier _before;
    private readonly EvolvingModifier _after;

    public SCItemReRollEvolvingResultPacket(
        ulong itemId,
        byte modifierIndex,
        bool changed,
        EvolvingModifier before,
        EvolvingModifier after)
        : base(SCOffsets.SCItemReRollEvolvingResultPacket, 5)
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

    private static void WriteModifier(PacketStream stream, EvolvingModifier modifier)
    {
        stream.Write(modifier.UnitAttributeId);
        stream.Write(modifier.UnitModifierTypeId);
        stream.Write(modifier.Value);
    }
}
