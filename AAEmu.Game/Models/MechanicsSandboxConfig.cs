namespace AAEmu.Game.Models;

public partial class AppConfiguration
{
    public MechanicsSandboxConfig MechanicsSandbox { get; set; } = new();
}

/// <summary>Explicit development controls, disabled in ordinary runtimes.</summary>
public sealed class MechanicsSandboxConfig
{
    private string _sceneName;
    private List<MechanicsSandboxServiceNpc> _services;
    private bool? _combatProfile;

    public bool Enabled { get; set; }
    // The development tool defaults to its combat build; ordinary runtimes remain disabled.
    public bool CombatProfile { get => _combatProfile ?? true; set => _combatProfile = value; }
    // Lazy defaults also cover existing instances created before a Hot Reload adds these fields.
    public string SceneName { get => _sceneName ??= "Laboratorio AA10"; set => _sceneName = value; }
    public string CharacterName { get; set; } = "Sandbox";
    public uint CharacterId { get; set; }
    public uint AccountId { get; set; }
    public uint WorldId { get; set; }
    public uint InstanceId { get; set; }
    public uint ZoneKey { get; set; } = 379;
    public MechanicsSandboxOrigin Origin { get; set; } = new();
    public uint DummyTemplateId { get; set; } = 7512;
    // ConfigurationBinder appends to existing collections. Slots belong to the JSON profile only.
    public List<MechanicsSandboxDummy> Dummies { get; set; } = [];
    public List<MechanicsSandboxServiceNpc> Services { get => _services ??= []; set => _services = value; }
}

public sealed class MechanicsSandboxOrigin
{
    public float X { get; set; }
    public float Y { get; set; }
    public float Z { get; set; }
    public float Rotation { get; set; }
}

public sealed class MechanicsSandboxDummy
{
    public float Forward { get; set; }
    public float Right { get; set; }
    public float Up { get; set; }
}

public sealed class MechanicsSandboxServiceNpc
{
    public uint TemplateId { get; set; }
    public string Role { get; set; }
    public float Forward { get; set; }
    public float Right { get; set; }
    public float Up { get; set; }
    public float Rotation { get; set; }
}
