using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.C2G;

/// <summary>
/// Notifies the server that the client has instantiated a quest-relevant client doodad.
/// </summary>
/// <remarks>
/// AA10 r575 writes the client-local BC object id at <c>+0x10</c> and the u32 template id at
/// <c>+0x14</c>. Native call sites belong to ClientDoodad; the packet carries no phase or position.
/// </remarks>
public class CSDoodadQuestNotiPacket() : GamePacket(CSOffsets.CSDoodadQuestNotiPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var doodadObjId = stream.ReadBc();
        var doodadTemplateId = stream.ReadUInt32();

        var character = Connection.ActiveChar;
        if (character?.Quests.ObserveQuestDoodad(doodadObjId, doodadTemplateId) == true)
            Logger.Debug(
                "CSDoodadQuestNoti: observed client doodad objId {0}, template {1}, zone {2}",
                doodadObjId, doodadTemplateId, character.Transform.ZoneId);
    }
}
