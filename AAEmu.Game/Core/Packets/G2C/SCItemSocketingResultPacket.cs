using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <remarks>
/// r575 opcode 0xCA. The client serializer at x2game.dll SHA-256
/// 2735819F39646EA07AF002BABC1EC105D091C4821E7B1290CB8525E809719F76,
/// RVA 0xA9C530, writes exactly these five body fields. The byte preceding <c>result</c> in the C++
/// object belongs to base packet metadata and is not part of the body.
/// </remarks>
public class SCItemSocketingResultPacket(
    byte result,
    ulong itemId,
    uint itemTemplateId,
    byte operation,
    bool success) : GamePacket(SCOffsets.SCItemSocketingResultPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(result);
        stream.Write(itemId);
        stream.Write(itemTemplateId);
        stream.Write(operation);
        stream.Write(success);
        return stream;
    }
}
