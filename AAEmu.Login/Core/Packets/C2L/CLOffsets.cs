namespace AAEmu.Login.Core.Packets.C2L;

public static class CLOffsets
{
    // ArcheAge Kakao 8.0.3.12 r558734 login opcodes. The modern backend is
    // intentionally kept, but its client-facing contract must remain AA8-native.
    public const ushort CARequestAuthPacket = 0x001;
    public const ushort CARequestWebAuthPacket = 0x002;
    public const ushort CAChallengeResponsePacket = 0x005;
    public const ushort CAChallengeResponse2Packet = 0x004;
    public const ushort CAOtpNumberPacket = 0x007;
    public const ushort CATestArsPacket = 0x006;
    public const ushort CAPcCertNumberPacket = 0x009;
    public const ushort CAListWorldPacket = 0x00c;
    public const ushort CAEnterWorldPacket = 0x00d;
    public const ushort CACancelEnterWorldPacket = 0xfff;
    public const ushort CARequestReconnectPacket = 0x00f;
    public const ushort CARequestAuthPWDPacket = 0x012;
    public const ushort CARequestVarifySNPacket = 0x013;
    public const ushort CAPongPacket = 0x014;
    public const ushort CARequestAuthKakaoPacket = 0x017;

    // Regional handlers retained by the modern backend but absent from AA8 Kakao.
    public const ushort CARequestAuthTencentPacket = 0xFFF;
    public const ushort CARequestAuthGameOnPacket = 0xFFF;
    public const ushort CARequestAuthTrionPacket = 0xFFF;
    public const ushort CARequestAuthMailRuPacket = 0xFFF;
}
