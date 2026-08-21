using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Claims the exact next reached reward tier from the normal or premium track.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class CSArchePassGetRewardItemPacket() : GamePacket(CSOffsets.CSArchePassGetRewardItemPacket, 1)
{
    public uint Tier { get; private set; }
    public bool Premium { get; private set; }

    public override void Read(PacketStream stream)
    {
        Tier = stream.ReadUInt32();
        Premium = stream.ReadBoolean();
    }

    public override void Execute() => ArchePassManager.Instance.TryClaimReward(Connection.ActiveChar, Tier, Premium);
}
