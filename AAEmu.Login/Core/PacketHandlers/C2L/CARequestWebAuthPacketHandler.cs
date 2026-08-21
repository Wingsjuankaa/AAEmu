using System.Text.Json;
using AAEmu.Login.Core.Authentication;
using AAEmu.Login.Core.Controllers;
using AAEmu.Login.Core.Network.Connections;
using AAEmu.Login.Core.Packets.C2L;
using AAEmu.Login.Core.Services;

namespace AAEmu.Login.Core.PacketHandlers.C2L;

/// <summary>
/// Handles the <see cref="CARequestWebAuthPacket"/> sent by clients launched in web/launcher
/// auth mode (passport flow).
/// </summary>
/// <remarks>
/// The client sends its launcher passport as a JSON blob in the <c>auth</c> field, e.g.
/// <c>{"source":"launcher","strUserToken":"...","StrUserName":"test","serverId":"1",...}</c>.
/// The simple AAEmu launcher places a versioned SHA-256 password proof in <c>strUserToken</c>.
/// The proof is validated through the normal password flow, so an existing account cannot be
/// impersonated with an arbitrary launcher token. When AutoAccount is enabled, first use creates
/// the account with that password proof.
/// Clients launched normally send <see cref="CARequestAuthPacket"/> instead.
/// </remarks>
public class CARequestWebAuthPacketHandler(ILoginController loginController)
    : ILoginPacketHandler<CARequestWebAuthPacket>
{
    private const string PasswordTokenPrefix = "aaemu-sha256-v1:";

    public async Task Execute(CARequestWebAuthPacket packet, ILoginSession session,
        CancellationToken cancellationToken)
    {
        var passport = ExtractLauncherPassport(packet.Auth);
        IAuthenticationFlow flow = passport is not null
            ? new PasswordAuthFlow(
                loginController,
                passport.Username,
                Password.FromSha256Hex(passport.PasswordHash),
                session.Connection.Ip)
            : new DeniedAuthFlow(LoginDeniedReason.BadAccount);
        await session.AuthenticateAsync(flow, cancellationToken);
    }

    private static LauncherPassport? ExtractLauncherPassport(string? auth)
    {
        if (string.IsNullOrWhiteSpace(auth))
            return null;

        try
        {
            using var doc = JsonDocument.Parse(auth);
            if (doc.RootElement.ValueKind == JsonValueKind.Object
                && doc.RootElement.TryGetProperty("StrUserName", out var name)
                && name.ValueKind == JsonValueKind.String
                && doc.RootElement.TryGetProperty("strUserToken", out var token)
                && token.ValueKind == JsonValueKind.String)
            {
                var username = name.GetString() ?? string.Empty;
                var tokenValue = token.GetString() ?? string.Empty;
                if (tokenValue.StartsWith(PasswordTokenPrefix, StringComparison.Ordinal))
                {
                    var hash = tokenValue[PasswordTokenPrefix.Length..];
                    if (hash.Length == 64 && hash.All(Uri.IsHexDigit))
                        return new LauncherPassport(username, hash);
                }
            }
        }
        catch (JsonException)
        {
            // Malformed passports are rejected by the caller.
        }

        return null;
    }

    private sealed record LauncherPassport(string Username, string PasswordHash);

    private sealed class DeniedAuthFlow(LoginDeniedReason reason) : IAuthenticationFlow
    {
        public Task<AuthFlowResult> StartAsync(ILoginClient client, CancellationToken cancellationToken) =>
            Task.FromResult<AuthFlowResult>(new AuthFlowResult.Denied(reason));
    }
}
