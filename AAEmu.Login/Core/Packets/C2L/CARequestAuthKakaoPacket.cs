using AAEmu.Commons.Network;
using AAEmu.Login.Core.Network.Login;

namespace AAEmu.Login.Core.Packets.C2L;

/// <summary>Launcher-token authentication used by ArcheAge Kakao 8.0.3.12 r558734.</summary>
public class CARequestAuthKakaoPacket() : LoginPacket(TypeId), ILoginPacket
{
    public new static ushort TypeId => CLOffsets.CARequestAuthKakaoPacket;

    public string AccessToken { get; private set; } = string.Empty;

    public override void Read(PacketStream stream)
    {
        _ = stream.ReadUInt32();
        _ = stream.ReadUInt32();
        _ = stream.ReadByte();
        _ = stream.ReadBoolean();
        _ = stream.ReadString();
        _ = stream.ReadString();
        AccessToken = stream.ReadString();
        _ = stream.ReadBoolean();
    }
}
