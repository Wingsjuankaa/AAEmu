using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>Initial AA10 ArchePass state page; the client accepts at most ten records per page.</summary>
public class SCArchePassesPacket(IReadOnlyCollection<ArchePassWireState> states, bool last)
    : GamePacket(SCOffsets.SCArchePassesPacket, 1)
{
    private readonly ArchePassWireState[] _states = states?.ToArray() ?? [];

    public override PacketStream Write(PacketStream stream)
    {
        if (_states.Length > 10)
            throw new InvalidOperationException("SCArchePassesPacket supports at most 10 records per page.");

        stream.Write(_states.Length);
        stream.Write(last);
        foreach (var state in _states)
            state.Write(stream);
        return stream;
    }
}

/// <summary>
/// Exact r575 ArchePass state serializer for a 32-byte aligned in-memory record. The final fields
/// map to the Lua/native normal and premium claim frontiers (the client misspells premium as
/// <c>Primium</c> in one accessor).
/// </summary>
public readonly record struct ArchePassWireState(
    int Type,
    long Point,
    byte Status,
    bool Premium,
    int LastRewardTier,
    int LastPremiumRewardTier)
{
    public void Write(PacketStream stream)
    {
        stream.Write(Type);
        stream.Write(Point);
        stream.Write(Status);
        stream.Write(Premium);
        stream.Write(LastRewardTier);
        stream.Write(LastPremiumRewardTier);
    }
}
