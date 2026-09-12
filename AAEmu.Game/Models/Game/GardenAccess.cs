using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.Game.Models.Game;

/// <summary>User-configured public Garden policy, separate from paid Patron membership.</summary>
public static class GardenAccess
{
    public const uint EntranceSkill = 43900;
    public const uint ContentId = 1;

    public static bool IsEntranceRequirement(UnitReqsKindType kind) =>
        kind is UnitReqsKindType.Level or UnitReqsKindType.GearScore;

    public static void EnsureContentGrant(List<AccountAttribute> attributes, uint accountId)
    {
        if (attributes.Any(a => a.KindId == (uint)AccountAttributeKind.Ulc && a.KindValue == ContentId))
            return;
        attributes.Add(new AccountAttribute
        {
            AccountId = accountId, KindId = (uint)AccountAttributeKind.Ulc,
            KindValue = ContentId, WorldId = 0, Count = 1,
            Starts = DateTime.UnixEpoch, Expires = DateTime.MaxValue
        });
    }
}
