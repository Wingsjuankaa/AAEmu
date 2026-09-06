using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class IpnyaCastWireTests
{
    private static SkillObject Context(bool feed)
    {
        if (feed)
        {
            var c=(SkillObjectEquipSlotReinforceMaterials)SkillObject.GetByType(SkillObjectType.EquipSlotReinforceMaterials);
            c.EquipSlot=17;c.MaterialId=0x12345678;c.AutoUseAaPoint=true;return c;
        }
        var e=(SkillObjectEquipSlotReinforceEffect)SkillObject.GetByType(SkillObjectType.EquipSlotReinforceEffect);
        e.EquipSlot=17;e.EffectLevel=5;return e;
    }

    [Test]
    [Arguments(true)]
    [Arguments(false)]
    public async Task StartedIncludesNativeExtraBeforeBothCastTimes(bool feed)
    {
        var id=feed?38363u:38664u;
        var packet=new SCSkillStartedPacket(id,0x1234,new SkillCasterUnit(1375),new SkillCastUnitTarget(1375),
            new Skill(new SkillTemplate { Id=id }),Context(feed)) { RealCastTimeMs=3500,BaseCastTimeMs=3500 };
        var bytes=packet.Write(new PacketStream()).GetBytes();
        // r575 AC3780 context22/23, common inputDirection, then two msec/10 and success tail.
        var golden=(feed?"DB950000":"08970000")+"3412005F0500005F0500"+
            (feed?"1611785634120100":"17110500")+"5E015E010000";
        await Assert.That(Convert.ToHexString(bytes)).IsEqualTo(golden);
    }

    [Test]
    [Arguments(true)]
    [Arguments(false)]
    public async Task FiredIncludesNativeExtraBeforeDelayAndPackedSkillId(bool feed)
    {
        var id=feed?38363u:38664u;
        var packet=new SCSkillFiredPacket(id,0x1234,new SkillCasterUnit(1375),new SkillCastUnitTarget(1375),
            new Skill(new SkillTemplate { Id=id }),Context(feed));
        var bytes=packet.Write(new PacketStream()).GetBytes();
        var golden="3412005F0500005F0500"+(feed?"1611785634120100":"17110500")+
            "0A000A000001"+(feed?"DB95":"0897")+"0000";
        await Assert.That(Convert.ToHexString(bytes)).IsEqualTo(golden);
    }
}
