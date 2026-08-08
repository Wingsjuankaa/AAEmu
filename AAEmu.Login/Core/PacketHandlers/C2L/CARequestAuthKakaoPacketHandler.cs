using AAEmu.Login.Core.Authentication;
using AAEmu.Login.Core.Controllers;
using AAEmu.Login.Core.Network.Connections;
using AAEmu.Login.Core.Packets.C2L;

namespace AAEmu.Login.Core.PacketHandlers.C2L;

/// <summary>
/// Development bridge for Kakao passport auth. The AA8 research runtime has no
/// Kakao identity service, so this explicit packet maps to the local test account.
/// </summary>
public class CARequestAuthKakaoPacketHandler(ILoginController loginController)
    : ILoginPacketHandler<CARequestAuthKakaoPacket>
{
    public async Task Execute(CARequestAuthKakaoPacket packet, ILoginSession session,
        CancellationToken cancellationToken)
    {
        var flow = new TokenAuthFlow(loginController, "test", session.Connection.Ip);
        await session.AuthenticateAsync(flow, cancellationToken);
    }
}
