using System.Net;
using AAEmu.Game.Models;
using AAEmu.Game.Models.Game.MechanicsSandbox;
using NetCoreServer;

namespace AAEmu.Game.Services.WebApi.Controllers;

/// <summary>Local-only observation of the real sandbox process; no chat or gameplay mutations.</summary>
internal sealed class MechanicsSandboxRuntimeController : BaseController
{
    private readonly Func<MechanicsSandboxConfig> _configuration;
    private readonly Func<string> _listenerHost;
    private readonly Func<MechanicsSandboxHotReload.RuntimeStatus> _snapshot;

    public MechanicsSandboxRuntimeController() : this(
        () => AppConfiguration.Instance.MechanicsSandbox,
        () => AppConfiguration.Instance.WebApiNetwork?.Host,
        MechanicsSandboxHotReload.Snapshot) { }

    internal MechanicsSandboxRuntimeController(Func<MechanicsSandboxConfig> configuration,
        Func<string> listenerHost, Func<MechanicsSandboxHotReload.RuntimeStatus> snapshot)
    {
        _configuration = configuration;
        _listenerHost = listenerHost;
        _snapshot = snapshot;
    }

    [WebApiGet("^/api/mechanics-sandbox/runtime$")]
    public HttpResponse Runtime(HttpRequest request)
    {
        if (!MechanicsSandboxHotReload.IsEnabled(_configuration()) ||
            !IPAddress.TryParse(_listenerHost(), out var address) || !IPAddress.IsLoopback(address))
            return JsonResponse(HttpStatusCode.Forbidden, new
            {
                success = false,
                message = "El diagnóstico requiere un sandbox vinculado y API limitada a loopback."
            });
        var value = _snapshot();
        return OkJson(new
        {
            success = true,
            pid = value.Pid,
            hotReloadSupported = value.HotReloadSupported,
            runningUnderWatch = value.RunningUnderWatch,
            updateCount = value.UpdateCount,
            lastUpdateUtc = value.LastUpdateUtc,
            diagnosticStamp = value.DiagnosticStamp,
            runtimeVersion = value.RuntimeVersion
        });
    }
}
