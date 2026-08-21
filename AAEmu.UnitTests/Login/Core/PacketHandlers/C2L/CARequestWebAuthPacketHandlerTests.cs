#nullable enable

using System.Net;
using AAEmu.Login.Core.Authentication;
using AAEmu.Login.Core.Controllers;
using AAEmu.Login.Core.Network.Connections;
using AAEmu.Login.Core.PacketHandlers.C2L;
using AAEmu.Login.Core.Packets.C2L;
using AAEmu.Login.Core.Services;
using AAEmu.Login.Models;

namespace AAEmu.UnitTests.Login.Core.PacketHandlers.C2L;

public class CARequestWebAuthPacketHandlerTests
{
    private static readonly IPAddress s_clientIp = IPAddress.Parse("192.0.2.25");
    private readonly Mock<ILoginController> _loginController = Mock.Of<ILoginController>();
    private readonly Mock<ILoginSession> _session = Mock.Of<ILoginSession>();
    private readonly Mock<ILoginConnection> _connection = Mock.Of<ILoginConnection>();

    public CARequestWebAuthPacketHandlerTests()
    {
        _connection.Ip.Returns(s_clientIp);
        _session.Connection.Returns(_connection.Object);
    }

    [Test]
    public async Task Execute_ValidPasswordToken_UsesNormalPasswordAuthentication()
    {
        const string Hash = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F";
        var packet = CreatePacket($$"""{"StrUserName":"jugador","strUserToken":"aaemu-sha256-v1:{{Hash}}"}""");
        IAuthenticationFlow? capturedFlow = null;
        _session.AuthenticateAsync(Any<IAuthenticationFlow>(), Any<CancellationToken>())
            .Callback((flow, _) => capturedFlow = flow);
        _loginController.Login("jugador", Password.FromSha256Hex(Hash), s_clientIp, Any<CancellationToken>())
            .Returns(new LoginResult(true, new AccountId(7), default));

        await new CARequestWebAuthPacketHandler(_loginController.Object)
            .Execute(packet, _session.Object, CancellationToken.None);

        await Assert.That(capturedFlow).IsNotNull();
        var result = await capturedFlow!.StartAsync(Mock.Of<ILoginClient>().Object, CancellationToken.None);
        await Assert.That(result).IsTypeOf<AuthFlowResult.Success>();
        _loginController.Login("jugador", Password.FromSha256Hex(Hash), s_clientIp, Any<CancellationToken>())
            .WasCalled(Times.Once);
    }

    [Test]
    [Arguments("{\"StrUserName\":\"jugador\",\"strUserToken\":\"testtoken\"}")]
    [Arguments("{not-json")]
    public async Task Execute_UnversionedOrMalformedToken_IsDenied(string auth)
    {
        var packet = CreatePacket(auth);
        IAuthenticationFlow? capturedFlow = null;
        _session.AuthenticateAsync(Any<IAuthenticationFlow>(), Any<CancellationToken>())
            .Callback((flow, _) => capturedFlow = flow);

        await new CARequestWebAuthPacketHandler(_loginController.Object)
            .Execute(packet, _session.Object, CancellationToken.None);

        await Assert.That(capturedFlow).IsNotNull();
        var result = await capturedFlow!.StartAsync(Mock.Of<ILoginClient>().Object, CancellationToken.None);
        var denied = await Assert.That(result).IsTypeOf<AuthFlowResult.Denied>();
        await Assert.That(denied.Reason).IsEqualTo(LoginDeniedReason.BadAccount);
    }

    private static CARequestWebAuthPacket CreatePacket(string auth)
    {
        var packet = new CARequestWebAuthPacket();
        typeof(CARequestWebAuthPacket).GetProperty(nameof(CARequestWebAuthPacket.Auth))!.SetValue(packet, auth);
        return packet;
    }
}
