using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Char.Creation
{
    public sealed class NativeCharacterCreationRequest
    {
        public string Name { get; internal set; }
        public byte Race { get; internal set; }
        public byte Gender { get; internal set; }
        public uint[] Body { get; internal set; }
        public UnitCustomModelParams CustomModel { get; internal set; }
        public byte[] Abilities { get; internal set; }
        public byte Level { get; internal set; }
        public int IntroZoneId { get; internal set; }
    }

    /// <summary>
    /// Exact request layout reconstructed from x2game.dll FUN_3997d1b0 and
    /// FUN_399a70b0. It consumes the whole payload or returns no request.
    /// </summary>
    public static class NativeCharacterCreationRequestWireCodec
    {
        public static bool TryRead(
            PacketStream stream,
            out NativeCharacterCreationRequest request,
            out string error)
        {
            request = null;
            error = string.Empty;
            if (stream == null)
            {
                error = "null create-character payload";
                return false;
            }

            try
            {
                var parsed = new NativeCharacterCreationRequest
                {
                    Name = stream.ReadString(),
                    Race = stream.ReadByte(),
                    Gender = stream.ReadByte(),
                    Body = new uint[7]
                };
                for (var index = 0; index < parsed.Body.Length; index++)
                    parsed.Body[index] = stream.ReadUInt32();

                parsed.CustomModel =
                    new UnitCustomModelParams(UnitCustomModelType.Face);
                parsed.CustomModel.Read(stream);
                parsed.Abilities = new byte[3];
                for (var index = 0; index < parsed.Abilities.Length; index++)
                    parsed.Abilities[index] = stream.ReadByte();
                parsed.Level = stream.ReadByte();
                parsed.IntroZoneId = stream.ReadInt32();

                if (stream.LeftBytes != 0)
                {
                    error =
                        $"create-character payload has {stream.LeftBytes} trailing bytes";
                    return false;
                }
                if (parsed.Level != NativeCharacterCreationCatalog.NativeLevel ||
                    parsed.IntroZoneId !=
                    NativeCharacterCreationCatalog.NativeIntroZoneSentinel)
                {
                    error =
                        $"create-character sentinels differ: level={parsed.Level}, " +
                        $"introZoneId={parsed.IntroZoneId}";
                    return false;
                }

                request = parsed;
                return true;
            }
            catch (Exception exception)
            {
                error = "malformed create-character payload: " + exception.Message;
                return false;
            }
        }
    }
}
