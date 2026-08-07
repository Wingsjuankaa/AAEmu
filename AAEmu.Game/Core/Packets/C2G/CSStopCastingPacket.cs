using System.Threading.Tasks;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSStopCastingPacket : GamePacket
    {
        public CSStopCastingPacket() : base(CSOffsets.CSStopCastingPacket, 5)
        {
        }

        public override async void Read(PacketStream stream)
        {
            var skillTlId = stream.ReadUInt16(); // sid
            var plotTlId = stream.ReadUInt16(); // tl; pid
            var objId = stream.ReadBc();

            if (Connection.ActiveChar.ObjId != objId)
                return;

            await TryStopCasting(Connection.ActiveChar, skillTlId, plotTlId);
        }

        public static async Task<bool> TryStopCasting(Unit unit, ushort skillTlId, ushort plotTlId)
        {
            if (unit == null)
                return false;

            // Plot-only skills perform their cast inside PlotTree and do not
            // create Unit.SkillTask. AA8 sends their timeline in the second
            // ushort (plotTlId), independently from the first SkillTask id.
            // A zero plot id falls back to the first id for compatibility with
            // older clients that did not split the two timelines.
            var plotState = unit.ActivePlotState;
            var effectivePlotTlId = plotTlId != 0 ? plotTlId : skillTlId;
            var stopped = false;
            if (plotState?.ActiveSkill?.TlId == effectivePlotTlId)
            {
                if (plotState.TryReleaseCastingUseable())
                {
                    NativeSkillLiveTrace.RecordCastingRelease(
                        plotState.ActiveSkill,
                        unit,
                        plotState.CastingPercent);
                    return true;
                }

                plotState.RequestCancellation();
                stopped = true;
            }

            // Keep a stable reference across the await: Stop() clears the
            // unit property and another thread may also finish the task.
            var skillTask = unit.SkillTask;
            if (skillTask?.Skill?.TlId != skillTlId)
                return stopped;

            await skillTask.Cancel();
            skillTask.Skill.Stop(unit);
            return true;
        }
    }
}
