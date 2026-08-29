using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <remarks>
/// The r575 serializer stores the timeline id in a four-byte native member but writes it through
/// the serializer's u16 slot (field name <c>tl</c>). The wire body is therefore exactly two bytes.
/// </remarks>
public class CSRebuildHouseTaxInfoPacket() : GamePacket(CSOffsets.CSRebuildHouseTaxInfoPacket, 1)
{
    public ushort HouseTimelineId { get; private set; }

    internal static ushort ReadHouseTimelineId(PacketStream stream) => stream.ReadUInt16();

    public override void Read(PacketStream stream)
    {
        HouseTimelineId = ReadHouseTimelineId(stream);
        HousingManager.Instance.RebuildHouseTaxInfo(Connection, HouseTimelineId);
    }
}
