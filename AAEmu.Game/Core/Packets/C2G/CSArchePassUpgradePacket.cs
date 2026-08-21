using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Upgrades the character's pass in progress to its premium reward track.
/// </summary>
/// <remarks>
/// packet has no body. Every parameterless C2S type folds onto that one function, so the
/// shared address is identical-COMDAT folding, not a base-class fall-through.
/// </remarks>
public class CSArchePassUpgradePacket() : GamePacket(CSOffsets.CSArchePassUpgradePacket, 1)
{
    public override void Read(PacketStream stream)
    {
    }

    public override void Execute() => ArchePassManager.Instance.TryUpgradePremium(Connection.ActiveChar);
}
