using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>Initial list of completed ArchePass mission bitsets.</summary>
public class SCCompletedArchePassesPacket(IReadOnlyCollection<CompletedArchePassWireState> states)
    : GamePacket(SCOffsets.SCCompletedArchePassesPacket, 1)
{
    private readonly CompletedArchePassWireState[] _states = states?.ToArray() ?? [];

    public override PacketStream Write(PacketStream stream)
    {
        if (_states.Length > 50)
            throw new InvalidOperationException("SCCompletedArchePassesPacket supports at most 50 records.");

        stream.Write(_states.Length);
        foreach (var state in _states)
        {
            stream.Write(state.Index);
            stream.Write(state.Body);
        }
        return stream;
    }
}

public readonly record struct CompletedArchePassWireState(int Index, ulong Body);
