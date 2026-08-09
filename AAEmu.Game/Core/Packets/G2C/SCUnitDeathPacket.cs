using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCUnitDeathPacket : GamePacket
    {
        private const uint NoKillerObjId = 0u;

        private readonly uint _objId;
        private readonly byte _killReason;
        private readonly Unit _killer;

        public SCUnitDeathPacket(uint objId, KillReason killReason, Unit killer = null) : base(SCOffsets.SCUnitDeathPacket, 5)
        {
            _objId = objId;
            _killReason = (byte)killReason;
            _killer = killer;
        }

        public override PacketStream Write(PacketStream stream)
        {
            stream.WriteBc(_objId);     // uid
            stream.Write(_killReason);  // killReason
            // AA8 wire contract proven by the last known-good 20:19 image.
            // FUN_39AB5D30 initializes a wider in-memory death-state block; it
            // is not the network serializer and its extra auto-resurrection
            // field must not be inserted into this packet.
            stream.Write(0u);          // resurrectionWaitingTime
            stream.Write(0u);          // specialResurrectionWaitingTime
            stream.Write(0);           // lostExp
            stream.Write((byte)0);     // deathDurabilityLossRatio
            // ---------------
            var killerId = _killer?.ObjId ?? NoKillerObjId;
            stream.WriteBc(killerId); // killer
            if (killerId == NoKillerObjId)
                return stream;
            // ---------------
            stream.Write((byte)0);     // GameType
            // ---------------
            stream.Write((ushort)0);   // killStreak
            stream.Write((byte)0);     // param1
            stream.Write((byte)0);     // param2
            stream.Write((byte)0);     // type (AA8 wire width)
            stream.Write(_killer.Name ?? string.Empty, true, false); // killerName

            return stream;
        }

        public override string Verbose()
        {
            return $" - victim={_objId}, reason={_killReason}, killer={_killer?.ObjId ?? NoKillerObjId}";
        }
    }
}
