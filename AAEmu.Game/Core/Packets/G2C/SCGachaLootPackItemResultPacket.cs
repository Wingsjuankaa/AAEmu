using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Items;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 Loot Gacha completion packet (opcode 0x2E3).</summary>
public sealed class SCGachaLootPackItemResultPacket(
    ErrorMessageType error,
    uint leftBatchCount,
    bool finish,
    IReadOnlyCollection<Item> items)
    : GamePacket(SCOffsets.SCGachaLootPackItemResultPacket, 1)
{
    public const int MaximumItemCount = 15;

    public override PacketStream Write(PacketStream stream)
    {
        stream.Write((short)error);
        if (error != ErrorMessageType.NoErrorMessage)
            return stream;

        var resultItems = (items ?? []).Take(MaximumItemCount).ToArray();
        stream.Write(leftBatchCount);
        stream.Write((uint)resultItems.Length);
        stream.Write(finish);
        foreach (var item in resultItems)
            stream.Write(item);
        return stream;
    }
}
