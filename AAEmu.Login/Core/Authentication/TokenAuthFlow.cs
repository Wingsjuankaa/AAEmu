using System.Net;
using AAEmu.Login.Core.Controllers;
using AAEmu.Login.Core.Network.Connections;

namespace AAEmu.Login.Core.Authentication;

/// <summary>
/// Trusted launcher-token flow used by the isolated AA8 Kakao research runtime.
/// </summary>
public class TokenAuthFlow(ILoginController loginController, string username, IPAddress clientIp)
    : IAuthenticationFlow
{
    public async Task<AuthFlowResult> StartAsync(ILoginClient client, CancellationToken cancellationToken)
    {
        var result = await loginController.LoginTrusted(username, clientIp, cancellationToken);
        return result.Success
            ? new AuthFlowResult.Success(result.AccountId, username)
            : new AuthFlowResult.Denied(result.DenialReason);
    }
}
