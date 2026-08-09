using System;
using System.Linq;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSAesXorKey_05_Packet : GamePacket
    {
        public CSAesXorKey_05_Packet() : base(CSOffsets.CSAesXorKey_05_Packet, 5)
        {

        }

        public override void Read(PacketStream stream)
        {
            _log.Info("CSAesXorKey_05_Packet : BEGIN");
            if (!CharacterListHandshakeWireCodec.TryReadReuseKeys(
                    stream,
                    out var error))
            {
                _log.Warn(
                    "Rejected in-session character-list handshake: {0}; payloadBytes={1}; payload={2}",
                    error,
                    stream.LeftBytes,
                    stream);
                return;
            }

            Connection.SendPacket(new SCGetSlotCountPacket(0));
            Connection.SendPacket(new SCAccountAttendancePacket(31));
            Connection.SendPacket(new SCRaceCongestionPacket());
            //Connection.SendPacket(new SCNotifyPacket());

            Connection.LoadAccount();
            var characters = Connection.Characters.Values.ToArray();

            if (characters.Length == 0)
            {
                Connection.SendPacket(new SCCharacterListPacket(true, characters));
            }
            else
            {
                for (var i = 0; i < characters.Length; i += 2)
                {
                    var last = characters.Length - i <= 2;
                    var temp = new Character[last ? characters.Length - i : 2];
                    Array.Copy(characters, i, temp, 0, temp.Length);
                    Connection.SendPacket(new SCCharacterListPacket(last, temp));
                }
            }
            _log.Info("CSAesXorKey_05_Packet : END");
        }
    }
}
