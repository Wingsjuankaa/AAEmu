using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSExecuteCraft() : GamePacket(CSOffsets.CSExecuteCraft, 1)
{
    public override void Read(PacketStream stream)
    {
        var craftId = stream.ReadUInt32();
        var objId = stream.ReadBc();
        var count = stream.ReadInt32();

        Logger.Debug("CSExecuteCraft, craftId : {0} , objId : {1}, count : {2}", craftId, objId, count);

        var character = Connection.ActiveChar;
        if (character is null)
            return;
        if (!CraftManager.Instance.TryGetCraft(craftId, out var craft))
        {
            character.SendErrorMessage(ErrorMessageType.CraftCantActAnyMore);
            return;
        }

        character.Craft.TryStart(craft, count, objId);
    }
}
