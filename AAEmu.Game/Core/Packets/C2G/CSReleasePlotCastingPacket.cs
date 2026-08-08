using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.C2G
{
    /// <summary>
    /// AA8 casting_useable input. The client emits this packet repeatedly while
    /// the skill key is pressed during an active plot cast.
    /// </summary>
    public class CSReleasePlotCastingPacket : GamePacket
    {
        public CSReleasePlotCastingPacket() : base(CSOffsets.CSReleasePlotCastingPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var payload = ReadPayload(stream);
            var actorObjId = payload.ActorObjId;
            // AA8 r558734 body (observed live): actor bc + uint16 + plot tl.
            // Treating the middle field as one byte shifted the timeline by a
            // byte, so every repeated-key release was rejected. Jumping still
            // worked because it travels through CSStopCasting instead.
            var mode = payload.Mode;
            var plotTlId = payload.PlotTlId;

            if (!TryRelease(Connection.ActiveChar, actorObjId, plotTlId))
            {
                _log.Debug(
                    "ReleasePlotCasting ignored actor={0} mode={1} plotTl={2} activeActor={3} activePlotTl={4}",
                    actorObjId, mode, plotTlId, Connection.ActiveChar?.ObjId,
                    Connection.ActiveChar?.ActivePlotState?.ActiveSkill?.TlId);
            }
        }

        public static (uint ActorObjId, ushort Mode, ushort PlotTlId) ReadPayload(PacketStream stream)
        {
            return (stream.ReadBc(), stream.ReadUInt16(), stream.ReadUInt16());
        }

        public static bool TryRelease(Unit unit, uint actorObjId, ushort plotTlId)
        {
            if (unit == null || unit.ObjId != actorObjId)
                return false;

            var state = unit.ActivePlotState;
            var skill = state?.ActiveSkill;
            if (skill?.TlId != plotTlId || !state.TryReleaseCastingUseable())
                return false;

            NativeSkillLiveTrace.RecordCastingRelease(skill, unit, state.CastingPercent);
            return true;
        }
    }
}
