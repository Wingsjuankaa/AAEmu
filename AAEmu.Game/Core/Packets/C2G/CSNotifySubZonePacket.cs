using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Tasks.Quests;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSNotifySubZonePacket() : GamePacket(CSOffsets.CSNotifySubZonePacket, 1)
{
    internal static readonly TimeSpan ClientDoodadQuestReactLoadDelay = TimeSpan.FromSeconds(3);

    public override void Read(PacketStream stream)
    {
        var subZoneId = stream.ReadUInt32();
        var character = Connection.ActiveChar;
        if (character == null)
            return;

        if (subZoneId != 0)
        {
            // A newer non-zero enter invalidates any older delayed replay. AA10
            // may emit zero immediately after enter, so the sentinel is ignored.
            var questReactEdgeVersion = character.Quests.MarkClientDoodadQuestReactEdge();
            character.SubZoneId = subZoneId; // needed to store Memory Tome points for Recall

            Logger.Info($"Enter RegionId: {subZoneId} by {character.Name} ({character.Id})");
            character.Portals.NotifySubZone(subZoneId);

            TaskManager.Instance.Schedule(
                new ClientDoodadQuestReactResyncTask(character, subZoneId, questReactEdgeVersion),
                ClientDoodadQuestReactLoadDelay);
        }
    }
}
