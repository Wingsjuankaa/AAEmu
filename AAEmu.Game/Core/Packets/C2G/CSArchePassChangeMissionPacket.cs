using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Parses the exact r575 request but deliberately rejects it: content-config keys 277-280 exist,
/// while their authoritative values do not.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class CSArchePassChangeMissionPacket() : GamePacket(CSOffsets.CSArchePassChangeMissionPacket, 1)
{
    public uint RealStep { get; private set; }

    public override void Read(PacketStream stream)
    {
        RealStep = stream.ReadUInt32();
    }

    public override void Execute() =>
        ArchePassManager.Instance.RejectMutation(Connection.ActiveChar, $"change mission realStep={RealStep}");
}
