using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Game.Units.Static;

namespace AAEmu.UnitTests.Game.Models.Game;

public class GardenAccessTests
{
    [Test]
    public async Task PublicGardenGrant_IsAccountWide_Idempotent_AndDoesNotGrantPatron()
    {
        foreach (var account in new uint[] { 1, 9000 })
        {
            var attributes = new List<AccountAttribute>();
            GardenAccess.EnsureContentGrant(attributes, account);
            GardenAccess.EnsureContentGrant(attributes, account);
            await Assert.That(attributes.Count).IsEqualTo(1);
            await Assert.That(attributes[0].AccountId).IsEqualTo(account);
            await Assert.That(attributes[0].KindId).IsEqualTo((uint)AccountAttributeKind.Ulc);
            await Assert.That(attributes[0].KindValue).IsEqualTo(1u);
            await Assert.That(attributes[0].IsExpired).IsFalse();
            var bytes = new SCAccountAttributeListPacket(attributes).Write(new PacketStream()).GetBytes();
            var body = new PacketStream(bytes);
            await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
            await Assert.That(body.ReadByte()).IsEqualTo((byte)3);
            await Assert.That(body.ReadUInt32()).IsEqualTo(1u);
            await Assert.That(body.ReadByte()).IsEqualTo((byte)0);
        }
    }

    [Test]
    [Arguments(7999, 0u, 8000u, false)]
    [Arguments(8000, 0u, 8000u, true)]
    [Arguments(11718, 0u, 8000u, true)]
    [Arguments(3000, 1u, 2999u, false)]
    [Arguments(2999, 1u, 2999u, true)]
    [Arguments(11718, 2u, 8000u, false)]
    public async Task GearScoreBounds(int score, uint comparison, uint threshold, bool expected)
    {
        await Assert.That(UnitReqs.MeetsGearScore(score, comparison, threshold)).IsEqualTo(expected);
        await Assert.That(SkillResultHelper.SkillResultErrorKeyToId(SkillResultKeys.skill_urk_gear_score))
            .IsEqualTo(SkillResult.UrkGearScore);
    }

    [Test]
    public async Task PublicEntranceRetainsOnlyLevelAndGear_AndRejectsNonCharacters()
    {
        foreach (var kind in Enum.GetValues<UnitReqsKindType>())
            await Assert.That(GardenAccess.IsEntranceRequirement(kind))
                .IsEqualTo(kind is UnitReqsKindType.Level or UnitReqsKindType.GearScore);
        var level = new UnitReqs { KindType = UnitReqsKindType.Level, Value1 = 55 };
        await Assert.That(level.Validate(new Unit { Level = 54 }, null).ResultKey).IsEqualTo(SkillResultKeys.skill_urk_level);
        await Assert.That(level.Validate(new Unit { Level = 55 }, null).ResultKey).IsEqualTo(SkillResultKeys.ok);
        var gear = new UnitReqs { KindType = UnitReqsKindType.GearScore, Value1 = 0, Value2 = 8000 };
        await Assert.That(gear.Validate(new Unit(), null).ResultKey).IsEqualTo(SkillResultKeys.skill_urk_gear_score);
        await Assert.That(SpecialEffect.IsImplemented(SpecialType.TeleportToIntegrationWorld)).IsTrue();
    }
}
