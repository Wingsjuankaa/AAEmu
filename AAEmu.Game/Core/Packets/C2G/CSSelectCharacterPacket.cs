using System;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.World.Zones;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSSelectCharacterPacket : GamePacket
    {
        public CSSelectCharacterPacket() : base(CSOffsets.CSSelectCharacterPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            _log.Info("CSSelectCharacterPacket : BEGIN");

            if (!CharacterSelectionWireCodec.TryRead(
                    stream,
                    out var characterId,
                    out var skipClientDriven,
                    out var error))
            {
                _log.Warn("Rejected character selection: {0}", error);
                return;
            }

            if (Connection.Characters.ContainsKey(characterId))
            {
                var character = Connection.Characters[characterId];
                character.Load();
                character.Connection = Connection;
                var houses = Connection.Houses.Values.Where(x => x.OwnerId == character.Id);

                Connection.ActiveChar = character;
                Connection.ActiveChar.ObjId = ObjectIdManager.Instance.GetNextId();

                Connection.SendPacket(new SCCharacterStatePacket(character));
                Connection.SendPacket(new SCGamePointInitedPacket(character)); //Connection.SendPacket(new SCCharacterGamePointsPacket(character));

                Connection.ActiveChar.Inventory.Send();
                Connection.SendPacket(new SCActionSlotsPacket(Connection.ActiveChar.Slots));

                // AA8 evaluates quest UnitReq kind 56 through the client-side
                // system-faction hierarchy. Send the complete catalogue before
                // either quest snapshot triggers the client's NPC marker pass.
                FactionManager.Instance.SendFactions(Connection.ActiveChar);

                // AA8 keeps the quest catalogue in the client compact, but the
                // active/completed state is authoritative server state.  Both
                // snapshots are required before the client can calculate NPC
                // quest availability and render quest markers.
                Connection.ActiveChar.Quests.Send();
                Connection.ActiveChar.Quests.SendCompleted();

                //Connection.ActiveChar.Actability.Send();
                //Connection.ActiveChar.Appellations.Send();

                //Connection.ActiveChar.Portals.Send();
                //Connection.ActiveChar.Friends.Send();
                //Connection.ActiveChar.Blocked.Send();

                //foreach (var house in houses)
                //{
                //    Connection.SendPacket(new SCHouseStatePacket(house));
                //}

                //foreach (var conflict in ZoneManager.Instance.GetConflicts())
                //{
                //    Connection.SendPacket(new SCConflictZoneStatePacket(conflict.ZoneGroupId, ZoneConflictType.Tension, conflict.NoKillMin[0] > 0 ? DateTime.Now.AddMinutes(conflict.NoKillMin[0]) : DateTime.MinValue));
                //}

                // Native AA8 faction relations remain a separate reconstruction
                // surface; do not send the historical relation catalogue.
                //FactionManager.Instance.SendRelations(Connection.ActiveChar);
                //ExpeditionManager.Instance.SendExpeditions(Connection.ActiveChar);

                //if (Connection.ActiveChar.Expedition != null)
                //{
                //    ExpeditionManager.Instance.SendExpeditionInfo(Connection.ActiveChar);
                //}

                Connection.ActiveChar.SendOption(1);
                Connection.ActiveChar.SendOption(2);
                Connection.ActiveChar.SendOption(5);

                _log.Info(
                    "CSSelectCharacterPacket : END (skipClientDriven={0})",
                    skipClientDriven);
            }
            else
            {
                // TODO ...
            }
        }
    }
}
