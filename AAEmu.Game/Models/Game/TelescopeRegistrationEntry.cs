using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Models.Game;

public class TelescopeRegistrationEntry
{
    private float _showPublicTransportRange;
    private float _showFishSchoolRange;
    private bool _showAllFishSchools;
    private float _showShipTelescopeRange;
    public Character Player { get; set; }

    public float ShowPublicTransportRange
    {
        get => _showPublicTransportRange;
        set
        {
            if (Math.Abs(_showPublicTransportRange - value) < 1f)
                return;
            _showPublicTransportRange = value;
            Player?.SendPacket(new SCTransferTelescopeToggledPacket(_showPublicTransportRange > 0, _showPublicTransportRange));
        }
    }

    public float ShowFishSchoolRange
    {
        get => _showFishSchoolRange;
        set
        {
            if (Math.Abs(_showFishSchoolRange - value) < 1f)
                return;
            var previous = EffectiveFishSchoolRange;
            _showFishSchoolRange = value;
            NotifyFishRange(previous);
        }
    }

    // Explicit GM mode, independent of boat buffs. Keep a finite display radius
    // for the native finder while the server selects the whole current instance.
    public const float WholeWorldFishDisplayRange = 1_000_000f;
    public float EffectiveFishSchoolRange => ShowAllFishSchools ? WholeWorldFishDisplayRange : ShowFishSchoolRange;
    public bool ShowAllFishSchools
    {
        get => _showAllFishSchools;
        set
        {
            var previous = EffectiveFishSchoolRange;
            _showAllFishSchools = value;
            NotifyFishRange(previous);
        }
    }

    private void NotifyFishRange(float previous)
    {
        var range = EffectiveFishSchoolRange;
        if (previous != range)
            Player?.SendPacket(new SCSchoolOfFishFinderToggledPacket(range > 0, range));
    }

    public float ShowShipTelescopeRange
    {
        get => _showShipTelescopeRange;
        set
        {
            if (Math.Abs(_showShipTelescopeRange - value) < 1f)
                return;
            _showShipTelescopeRange = value;
            // TODO: Implement Ship radar
            Player?.SendPacket(new SCTelescopeToggledPacket(_showShipTelescopeRange > 0, _showShipTelescopeRange));
        }
    }

    public bool IsActive => ShowPublicTransportRange > 0 || EffectiveFishSchoolRange > 0 || ShowShipTelescopeRange > 0;
}
