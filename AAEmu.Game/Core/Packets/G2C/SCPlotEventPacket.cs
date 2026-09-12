using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Skills.Plots;

namespace AAEmu.Game.Core.Packets.G2C;

/// <summary>
/// Trailing <c>inputDirection</c> u8 is mandatory; omitting it desyncs the SC stream
/// (<c>sc error; cur=227 prev=…</c> → System:Quit).
/// </summary>
public class SCPlotEventPacket(
    ushort tl,
    uint eventId,
    uint skillId,
    PlotObject caster,
    PlotObject target,
    uint objId,
    ushort castingTime,
    byte flag,
    ulong itemId = 0L,
    IReadOnlyList<uint> targetUnitIds = null,
    byte inputDirection = 0,
    ushort channelingTime = 0)
    : GamePacket(SCOffsets.SCPlotEventPacket, 1)
{
    public override PacketStream Write(PacketStream stream)
    {
        stream.Write(tl);      // u16 tl
        stream.Write(eventId); // u32 eventId
        stream.Write(skillId); // u32 skillId
        stream.Write(caster);  // PlotObj (type1=bc / type2=pos+rots+bcs)
        stream.Write(target);
        stream.Write(itemId);  // u64 item
        stream.WriteBc(objId);
        stream.Write(castingTime);
        stream.WriteBc(0);
        stream.Write(channelingTime);
        // r575 reader RVA 0xAB74D0: count followed by that many distinct unit references.
        // POSITION is carried by PlotObj; it is never a synthetic unit in this list.
        var ids = targetUnitIds ?? Array.Empty<uint>();
        stream.Write(checked((byte)ids.Count));
        foreach (var id in ids)
            stream.WriteBc(id);
        stream.Write(flag);
        if ((flag & 8) != 0)
        {
            for (var i = 0; i < 13; i++)
                stream.Write(0);
        }
        stream.Write(inputDirection); // ALWAYS present — was missing; caused client quit on 10752
        return stream;
    }
}
