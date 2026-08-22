using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Char;

/// <summary>
/// Handles the shared r575 invitation response for battlefields and native dungeon entry.
/// </summary>
/// <remarks>
/// Field order, widths and names come from the 10.0.2.13 client's serializer, which passes each
/// value's name alongside the value:
/// </remarks>
public class CSInvitationAnswerPacket() : GamePacket(CSOffsets.CSInvitationAnswerPacket, 1)
{
    public int InvitationTime { get; private set; }
    public bool Acceptance { get; private set; }

    public override void Read(PacketStream stream)
    {
        InvitationTime = stream.ReadInt32();
        Acceptance = stream.ReadBoolean();

        if (!TryHandle(Connection.ActiveChar, IndunManager.Instance, Acceptance, InvitationTime))
            Logger.Debug("CSInvitationAnswer ignored: no pending instant game or dungeon invitation");
    }

    internal static bool TryHandle(
        Character character,
        IIndunManager indunManager,
        bool accepted,
        int invitationTime)
    {
        if (character == null)
            return false;

        if (character.CurrentInstantGame != null)
        {
            character.CurrentInstantGame.PlayerInviteResponse(
                character,
                accepted,
                unchecked((ulong)(uint)invitationTime));
            return true;
        }

        return indunManager.RespondToDungeonInvitation(character, accepted, invitationTime);
    }
}
