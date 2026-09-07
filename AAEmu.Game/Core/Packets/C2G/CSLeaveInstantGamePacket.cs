using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSLeaveInstantGamePacket() : GamePacket(CSOffsets.CSLeaveInstantGamePacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var isIndunMatch = stream.LeftBytes > 0 && stream.ReadByte() != 0;
        var character = Connection.ActiveChar;
        if (character == null)
            return;
        if (isIndunMatch)
        {
            IndunMatchmakingManager.Instance.TryLeaveIndunMatch(character);
            return;
        }
        TryLeave(character, IndunManager.Instance);
    }

    /// <summary>
    /// Routes the shared r575 exit request to the kind of instance the character is currently in.
    /// The client uses CSLeaveInstantGame both for battlefields and for the native dungeon exit
    /// button attached to the zone-name informer.
    /// </summary>
    internal static bool TryLeave(Character character, IIndunManager indunManager)
    {
        if (character == null)
            return false;

        if (character.CurrentInstantGame != null)
        {
            character.CurrentInstantGame.LeaveInstantGame(character);
            return true;
        }

        return indunManager.RequestLeaveInstance(character);
    }
}
