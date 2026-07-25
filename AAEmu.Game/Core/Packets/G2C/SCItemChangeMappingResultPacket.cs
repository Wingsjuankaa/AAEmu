using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Core.Packets.G2C
{
    /// <summary>
    /// Native Kakao 8.0 awakening result (opcode 0x344).
    ///
    /// x2game.dll FUN_399a1cf0 serializes two complete item snapshots followed
    /// by the result byte and mapping-group id. FUN_393a3ff0 consumes result
    /// values 0/1/2 as success/fail/fail-and-disable respectively.
    /// </summary>
    public sealed class SCItemChangeMappingResultPacket : GamePacket
    {
        private readonly Item _before;
        private readonly Item _after;
        private readonly ItemChangeMappingResult _result;
        private readonly uint _mappingGroupId;

        public SCItemChangeMappingResultPacket(
            Item before,
            Item after,
            ItemChangeMappingResult result,
            uint mappingGroupId)
            : base(SCOffsets.SCItemChangeMappingResultPacket, 5)
        {
            _before = before;
            _after = after;
            _result = result;
            _mappingGroupId = mappingGroupId;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write(_before);
            stream.Write(_after);
            stream.Write((byte)_result);
            stream.Write(_mappingGroupId);
            return stream;
        }
    }
}
