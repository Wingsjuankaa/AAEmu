using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;

namespace AAEmu.Game.Core.Packets.G2C;

public class SCAccountAttendancePacket(long[] times = null, bool[] archelife = null)
    : GamePacket(SCOffsets.SCAccountAttendancePacket, 1)
{
    // Body: a FIXED 31-entry array of { "time" u64 (ISerialize vtbl+0x78), "isArchelife" bool (vtbl+0xF8) }.
    // length prefix. Represents the monthly attendance calendar; zero entries = nothing claimed.
    public const int Days = 31;
    private readonly long[] _times = Validate(times, nameof(times));
    private readonly bool[] _archelife = Validate(archelife, nameof(archelife));

    public override PacketStream Write(PacketStream stream)
    {
        for (var i = 0; i < Days; i++)
        {
            stream.Write(_times[i]);
            stream.Write(_archelife[i]);
        }
        return stream;
    }

    private static T[] Validate<T>(T[] values, string parameterName)
    {
        values ??= new T[Days];
        if (values.Length != Days)
            throw new ArgumentException($"Account Attendance requires exactly {Days} entries.", parameterName);
        return values;
    }
}
