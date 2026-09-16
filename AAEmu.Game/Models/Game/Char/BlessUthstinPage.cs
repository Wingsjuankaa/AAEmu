namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// One Bless Uthstin stat page. Applied values are signed — a drop can go negative.
/// </summary>
public sealed class BlessUthstinPage
{
    public int[] Stats { get; } = new int[5];
    public int NormalApplyCount { get => ApplyNormalCount; set => ApplyNormalCount = value; }
    public int SpecialApplyCount { get => ApplySpecialCount; set => ApplySpecialCount = value; }
    public int Strength { get => Stats[0]; set => Stats[0] = value; }
    public int Dexterity { get => Stats[1]; set => Stats[1] = value; }
    public int Stamina { get => Stats[2]; set => Stats[2] = value; }
    public int Intelligence { get => Stats[3]; set => Stats[3] = value; }
    public int Spirit { get => Stats[4]; set => Stats[4] = value; }
    public int ApplyNormalCount { get; set; }
    public int ApplySpecialCount { get; set; }

    public int GetStat(int kind) => kind switch
    {
        0 => Strength,
        1 => Dexterity,
        2 => Stamina,
        3 => Intelligence,
        4 => Spirit,
        _ => 0
    };

    public void SetStat(int kind, int value)
    {
        switch (kind)
        {
            case 0: Strength = value; break;
            case 1: Dexterity = value; break;
            case 2: Stamina = value; break;
            case 3: Intelligence = value; break;
            case 4: Spirit = value; break;
        }
    }

    public BlessUthstinPage Clone() => new()
    {
        Strength = Strength,
        Dexterity = Dexterity,
        Stamina = Stamina,
        Intelligence = Intelligence,
        Spirit = Spirit,
        ApplyNormalCount = ApplyNormalCount,
        ApplySpecialCount = ApplySpecialCount
    };

    public void CopyFrom(BlessUthstinPage other)
    {
        other ??= new BlessUthstinPage();
        Strength = other.Strength;
        Dexterity = other.Dexterity;
        Stamina = other.Stamina;
        Intelligence = other.Intelligence;
        Spirit = other.Spirit;
        ApplyNormalCount = other.ApplyNormalCount;
        ApplySpecialCount = other.ApplySpecialCount;
    }

    public void Clear()
    {
        Strength = 0;
        Dexterity = 0;
        Stamina = 0;
        Intelligence = 0;
        Spirit = 0;
        ApplyNormalCount = 0;
        ApplySpecialCount = 0;
    }
}
