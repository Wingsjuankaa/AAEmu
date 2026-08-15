using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Awakening outcome for r575 (opcode D4): full item before, full item after, mapping id and result
/// byte. Result 0 is success; a nonzero value is failure.
/// </summary>
public class SCItemChangeMappingResultPacket : GamePacket
{
    private readonly byte[] _before;
    private readonly Item _after;
    private readonly uint _mappingId;
    private readonly byte _result;

    public SCItemChangeMappingResultPacket(byte[] before, Item after, uint mappingId, byte result)
        : base(SCOffsets.SCItemChangeMappingResultPacket, 1)
    {
        _before = before;
        _after = after;
        _mappingId = mappingId;
        _result = result;
    }

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(_before, false);
        _after.Write(stream);
        stream.Write(_mappingId);
        stream.Write(_result);
        return stream;
    }
}
