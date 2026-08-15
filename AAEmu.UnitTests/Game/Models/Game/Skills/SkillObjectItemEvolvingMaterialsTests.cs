using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

/// <summary>
/// Pins the synthesis skill-object wire format against a real 10.0.2.13 client capture.
/// </summary>
public class SkillObjectItemEvolvingMaterialsTests
{
    /// <summary>
    /// CSStartSkill body captured while confirming a synthesis of Explorer's Staff (47788):
    /// skillId 30666, caster unit 719, item target 0x010000FD, skill object flag 8.
    /// </summary>
    private const string CapturedCastBody =
        "CA77000000CF020003CF0200FD00000100000000ACBA0000000830000801000100000000" +
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000";

    private static PacketStream CapturedCast()
    {
        var stream = new PacketStream();
        stream.Insert(0, Convert.FromHexString(CapturedCastBody));
        return stream;
    }

    [Test]
    public async Task CapturedCast_ParsesEndToEndWithNothingLeftOver()
    {
        var stream = CapturedCast();

        await Assert.That(stream.ReadUInt32()).IsEqualTo(30666u);

        var caster = SkillCaster.GetByType((SkillCasterType)stream.ReadByte());
        caster.Read(stream);
        await Assert.That(caster).IsTypeOf<SkillCasterUnit>();

        var target = SkillCastTarget.GetByType((SkillCastTargetType)stream.ReadByte());
        target.Read(stream);
        var itemTarget = target as SkillCastItemTarget;
        await Assert.That(itemTarget).IsNotNull();
        await Assert.That(itemTarget!.Id).IsEqualTo(0x010000FDul);
        await Assert.That(itemTarget.Type1).IsEqualTo(47788u); // Explorer's Staff

        // The type lives in the low 6 bits; masking with 15 would silently mis-read types 16 and up.
        var flag = stream.ReadByte();
        await Assert.That(flag & 0x3f).IsEqualTo((int)SkillObjectType.ItemEvolvingMaterials);

        var skillObject = SkillObject.GetByType((SkillObjectType)(flag & 0x3f));
        skillObject.Read(stream);
        var materials = skillObject as SkillObjectItemEvolvingMaterials;
        await Assert.That(materials).IsNotNull();
        await Assert.That(materials!.MaterialItemIds.Length).IsEqualTo(SkillObjectItemEvolvingMaterials.MaterialSlots);
        await Assert.That(materials.UsedMaterialItemIds.ToList()).IsEquivalentTo([0x01000108ul]);
        await Assert.That(materials.AutoUseAaPoint).IsFalse();

        _ = stream.ReadByte(); // inputDirection, common to every skill-object type

        // Every byte accounted for: a leftover here is a field this reader is dropping.
        await Assert.That(stream.Count - stream.Pos).IsEqualTo(0);
    }

    [Test]
    public async Task MaterialSlots_RoundTrip()
    {
        // GetByType is what stamps Flag, so build it the way the packet readers do.
        var written = (SkillObjectItemEvolvingMaterials)SkillObject.GetByType(SkillObjectType.ItemEvolvingMaterials);
        written.MaterialItemIds = [0x01000108ul, 0, 0x0100020Aul, 0, 0, 0];
        written.AutoUseAaPoint = true;

        var stream = new PacketStream();
        written.Write(stream);
        stream.Rollback();

        await Assert.That((SkillObjectType)stream.ReadByte()).IsEqualTo(SkillObjectType.ItemEvolvingMaterials);
        var read = new SkillObjectItemEvolvingMaterials();
        read.Read(stream);

        await Assert.That(read.MaterialItemIds).IsEquivalentTo(written.MaterialItemIds);
        await Assert.That(read.UsedMaterialItemIds.ToList()).IsEquivalentTo([0x01000108ul, 0x0100020Aul]);
        await Assert.That(read.AutoUseAaPoint).IsTrue();
    }

    [Test]
    public async Task OversizedPayload_IsConsumedForAlignmentButRejectedBySynthesis()
    {
        var stream = new PacketStream();
        stream.Write((ushort)(7 * sizeof(ulong)));
        for (ulong id = 1; id <= 7; id++)
            stream.Write(id);
        stream.Write(true);
        stream.Write((byte)0x5a);
        stream.Rollback();

        var materials = new SkillObjectItemEvolvingMaterials();
        materials.Read(stream);

        await Assert.That(materials.HasTooManySlots).IsTrue();
        await Assert.That(materials.HasValidWireShape).IsFalse();
        await Assert.That(materials.MaterialItemIds.Length).IsEqualTo(6);
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
    }

    [Test]
    public async Task PartialIdPayload_IsConsumedForAlignmentButRejectedBySynthesis()
    {
        var stream = new PacketStream();
        stream.Write((ushort)9);
        stream.Write(123ul);
        stream.Write((byte)0xff);
        stream.Write(false);
        stream.Write((byte)0x5a);
        stream.Rollback();

        var materials = new SkillObjectItemEvolvingMaterials();
        materials.Read(stream);

        await Assert.That(materials.HasMalformedLength).IsTrue();
        await Assert.That(materials.HasValidWireShape).IsFalse();
        await Assert.That(stream.ReadByte()).IsEqualTo((byte)0x5a);
    }
}
