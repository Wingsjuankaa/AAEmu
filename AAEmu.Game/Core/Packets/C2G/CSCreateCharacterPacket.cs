using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char.Creation;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSCreateCharacterPacket : GamePacket
    {
        public CSCreateCharacterPacket() : base(CSOffsets.CSCreateCharacterPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var payload = stream.GetBytes();
            if (!NativeCharacterCreationRequestWireCodec.TryRead(
                    stream,
                    out var request,
                    out var error))
            {
                _log.Warn(
                    "Rejected malformed AA8 create-character payload: {0}; " +
                    "bytes={1}; payload={2}",
                    error,
                    payload.Length,
                    System.BitConverter.ToString(payload).Replace("-", string.Empty));
                Connection.SendPacket(new SCCharacterCreationFailedPacket(3));
                return;
            }

            CharacterManager.Instance.Create(
                Connection,
                request.Name,
                request.Race,
                request.Gender,
                request.Body,
                request.CustomModel,
                request.Abilities,
                request.Level,
                request.IntroZoneId);
        }
    }
}
