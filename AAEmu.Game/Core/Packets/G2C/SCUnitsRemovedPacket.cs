using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCUnitsRemovedPacket : GamePacket
    {
        private readonly uint[] _ids;
        public const int MaxCountPerPacket = 500;

        public SCUnitsRemovedPacket(uint[] ids) : base(SCOffsets.SCUnitsRemovedPacket, 5)
        {
            if (ids == null)
                throw new System.ArgumentNullException(nameof(ids));
            if (ids.Length > MaxCountPerPacket)
                throw new System.ArgumentOutOfRangeException(
                    nameof(ids),
                    $"AA8 accepts at most {MaxCountPerPacket} unit IDs per packet.");

            _ids = ids;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((ushort) _ids.Length);
            foreach (var id in _ids)
                stream.WriteBc(id);

            return stream;
        }
    }
}
