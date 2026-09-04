namespace AAEmu.Game.Models.Game.Char;

/// <summary>
/// Existing portal_visited_district.subzone is a signed INT containing legacy subzone ids.
/// Bit 30 distinguishes new native district visits without changing SQL or the client wire.
/// Untagged historical visits retain their old catalogue interpretation on load.
/// </summary>
internal static class PortalVisitKey
{
    internal const uint DistrictTag = 1u << 30;
    internal const uint SubZoneTag = 1u << 29;
    internal static uint ForSubZone(uint subZoneId) => subZoneId is > 0 and < SubZoneTag
        ? SubZoneTag | subZoneId
        : throw new ArgumentOutOfRangeException(nameof(subZoneId));
    internal static uint ForDistrict(uint districtId) => districtId is > 0 and < DistrictTag
        ? DistrictTag | districtId
        : throw new ArgumentOutOfRangeException(nameof(districtId));

    internal static bool IsDistrict(uint key) => (key & DistrictTag) != 0;
    internal static bool IsSubZone(uint key) => (key & SubZoneTag) != 0;
    internal static uint SubZoneId(uint key) => key & ~SubZoneTag;
    internal static uint DistrictId(uint key) => key & ~DistrictTag;
}
