using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSCancelInstantGamePacket() : GamePacket(CSOffsets.CSCancelInstantGamePacket, 1)
{
    public override void Read(PacketStream stream)
    {
        // Empty struct
        Logger.Debug("CancelInstantGame");

        if (!TryCancelDungeonInvitation(Connection.ActiveChar, IndunManager.Instance))
            InstantGameManager.Instance.WithdrawFromBattlefield(Connection.ActiveChar);
    }

    internal static bool TryCancelDungeonInvitation(
        Models.Game.Char.Character character,
        IIndunManager indunManager)
    {
        return character != null &&
               indunManager.RespondToDungeonInvitation(character, false);
    }
}
