using System;

using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Initializes the client's world-content filters and the derived NPC quest indexes.
    /// An empty filter pack is the native "no filter config" mode and enables all local content.
    /// </summary>
    public class SCFilterPacket : GamePacket
    {
        private readonly byte[] _filterBuffer;

        public SCFilterPacket(byte[] filterBuffer = null) : base(SCOffsets.SCFilterPacket, 5)
        {
            _filterBuffer = filterBuffer ?? Array.Empty<byte>();
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((uint)_filterBuffer.Length);
            stream.Write(_filterBuffer, false);
            return stream;
        }
    }
}
