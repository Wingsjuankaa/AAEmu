using System.Threading.Tasks;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.C2G;

public class CSStopCastingPacket() : GamePacket(CSOffsets.CSStopCastingPacket, 1)
{
    public override void Read(PacketStream stream)
    {
        var tlId = stream.ReadUInt16(); // sid
        var plotTlId = stream.ReadUInt16(); // tl; pid
        var objId = stream.ReadBc();

        if (Connection.ActiveChar.ObjId != objId)
        {
            Logger.Warn($"Player {Connection.ActiveChar.Name} (ObjId {Connection.ActiveChar.ObjId}) is trying to stop casting a skill on object {objId} using TlId {tlId} and plotTlId {plotTlId}");
            return;
        }

        if (plotTlId != 0 && Connection.ActiveChar.ActivePlotState != null)
        {
            if (Connection.ActiveChar.ActivePlotState.ActiveSkill.TlId == plotTlId)
            {
                Connection.ActiveChar.ActivePlotState.RequestCancellation();
            }
            else
            {
                Connection.SendPacket(new SCPlotCastingStoppedPacket(plotTlId, 0, 1));
                Connection.SendPacket(new SCPlotChannelingStoppedPacket(plotTlId, 0, 1));
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

        if (Connection.ActiveChar.SkillTask == null || Connection.ActiveChar.SkillTask.Skill.TlId != tlId)
        {
            Logger.Warn($"Stop requested, but no skill active? Tl: {tlId}, Pid: {plotTlId}, objId: {objId}, Character: {Connection.ActiveChar.Name}");
            return;
        }

        Connection.ActiveChar.SkillTask.Cancel();

        if (Connection.ActiveChar.SkillTask is EndChannelingTask ect)
        {
            Connection.ActiveChar.SkillTask.Skill.Stop(Connection.ActiveChar, ect._channelDoodad);
        }
        else
        {
            Connection.ActiveChar.SkillTask.Skill.Stop(Connection.ActiveChar);
        }
    }
}
