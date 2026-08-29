using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

public readonly record struct HousingRebuildTaxEntry(
    int BuildingTax,
    bool ValidTax,
    double PaidDuration,
    int WeeklyPayment,
    int DominionTaxRate);

/// <summary>
/// Native r575 rebuild-tax response. The serializer names the fields tl, dr, count and then
/// bt/vt/pd/wp/dtr; pd is a double in the 24-byte native entry, not the historical AA8 float.
/// </summary>
public sealed class SCRebuildHouseTaxInfoPacket(
    ushort tl,
    int dominionTaxRate,
    IReadOnlyList<HousingRebuildTaxEntry> entries)
    : GamePacket(SCOffsets.SCRebuildHouseTaxInfoPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        var safeEntries = entries?.Take(100).ToArray() ?? [];
        stream.Write(tl);
        stream.Write(dominionTaxRate);
        stream.Write((uint)safeEntries.Length);
        foreach (var entry in safeEntries)
        {
            stream.Write(entry.BuildingTax);
            stream.Write(entry.ValidTax);
            stream.Write(entry.PaidDuration);
            stream.Write(entry.WeeklyPayment);
            stream.Write(entry.DominionTaxRate);
        }
        return stream;
    }
}
