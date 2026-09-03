using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>AA10 r575 Loot Gacha acquisition log (opcode 0x2E2).</summary>
public sealed class SCGachaLootPackItemLogPacket(IReadOnlyCollection<GachaLootLogEntry> entries)
    : GamePacket(SCOffsets.SCGachaLootPackItemLogPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        var rows = (entries ?? []).Take(byte.MaxValue).ToArray();
        stream.Write((byte)rows.Length);
        foreach (var row in rows)
        {
            stream.Write(row.ItemType);
            stream.Write(row.ItemGrade);
            stream.Write(row.StackSize);
        }
        return stream;
    }
}

public readonly record struct GachaLootLogEntry(uint ItemType, byte ItemGrade, int StackSize);
