using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCDoodadRemovedPacket : GamePacket
    {
        private readonly uint _id;
        private readonly bool _finalRemoval;

        public SCDoodadRemovedPacket(uint id, bool finalRemoval = false) : base(SCOffsets.SCDoodadRemovedPacket, 5)
        {
            _id = id;
            _finalRemoval = finalRemoval;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_id);
            // AA8 uses false when an object merely leaves the observer's region.
            // True activates the additional retirement path used when the
            // server permanently removes an ephemeral doodad and its phase FX.
            stream.Write(_finalRemoval);
            return stream;
        }

        public override string Verbose()
        {
            return $" - objId={_id}, finalRemoval={_finalRemoval}";
        }
    }
}
