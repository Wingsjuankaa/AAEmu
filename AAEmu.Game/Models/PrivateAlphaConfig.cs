namespace AAEmu.Game.Models;

public partial class AppConfiguration
{
    public PrivateAlphaConfig PrivateAlpha { get; set; } = new();
}

public sealed class PrivateAlphaConfig
{
    public bool Enabled { get; set; }
    public int MaxGoldPerRequest { get; set; } = 10000;
    public int LaborCap { get; set; } = 5000;
    public int MaxItemCount { get; set; } = 1000;
}
