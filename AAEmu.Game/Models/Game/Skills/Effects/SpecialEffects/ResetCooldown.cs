using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;

public class ResetCooldown : SpecialEffectAction
{
    protected override SpecialType SpecialEffectActionType => SpecialType.ResetCooldown;

    public override void Execute(BaseUnit caster,
        SkillCaster casterObj,
        BaseUnit target,
        SkillCastTarget targetObj,
        CastAction castObj,
        Skill skill,
        SkillObject skillObject,
        DateTime time,
        int value1,
        int value2,
        int value3,
        int value4)
    {
        Execute(caster, casterObj, target, targetObj, castObj, skill, skillObject, time,
            value1, value2, value3, value4, 0, 0, 0);
    }

    public override void Execute(BaseUnit caster, SkillCaster casterObj, BaseUnit target, SkillCastTarget targetObj,
        CastAction castObj, Skill skill, SkillObject skillObject, DateTime time,
        int skillId, int tagId, int gcd, int resetSkillTags, int resetTaggedSkills, int resetTaggedSkillTags, int unused)
    {
        if (caster is not Character character)
            return;

        character.SendPacket(ApplyReset(character, skillId, tagId, gcd == 1,
            resetSkillTags == 1, resetTaggedSkills == 1, resetTaggedSkillTags == 1));
    }

    // Native r575 consumer RVA 0x4C8E00 (dedicate SHA in the Battlerage dossier)
    // distinguishes a cooldown-tag key from the skills carrying that tag. The
    // final flags are "tagged skill", not "toggle skill". Deflect's row 4636
    // uses (skill=0, tag=415, gc=1, rstc=0, rtsc=1, rtstc=1).
    internal static SCSkillCooldownResetPacket ApplyReset(Character character, int skillId, int tagId,
        bool gcd, bool resetSkillTags, bool resetTaggedSkills, bool resetTaggedSkillTags)
    {
        void ResetSkill(uint id, bool resetTags)
        {
            character.Cooldowns.RemoveCooldown(id);
            if (!resetTags)
                return;
            foreach (var tag in SkillManager.Instance.GetSkillTemplate(id)?.CooldownTags ?? [])
                character.Cooldowns.RemoveTagCooldown((uint)tag);
        }

        if (skillId > 0)
            ResetSkill((uint)skillId, resetSkillTags);
        if (tagId > 0)
        {
            character.Cooldowns.RemoveTagCooldown((uint)tagId);
            if (resetTaggedSkills)
                foreach (var id in SkillManager.Instance.GetSkillsByTag((uint)tagId))
                    ResetSkill(id, resetTaggedSkillTags);
        }
        if (gcd)
            lock (character.GcdLock)
                character.GlobalCooldown = DateTime.MinValue;

        return new SCSkillCooldownResetPacket(character, (uint)Math.Max(0, skillId), (uint)Math.Max(0, tagId),
            gcd, resetSkillTags, resetTaggedSkills, resetTaggedSkillTags);
    }
}
