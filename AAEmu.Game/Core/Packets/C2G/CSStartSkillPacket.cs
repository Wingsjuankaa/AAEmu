using AAEmu.Commons.Network;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSStartSkillPacket : GamePacket
    {
        public CSStartSkillPacket() : base(CSOffsets.CSStartSkillPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            var skillId = stream.ReadUInt32();
            // if (skillId == 2 || skillId == 3 || skillId == 4)
            //     return;

            var skillCasterType = stream.ReadByte(); // кто применяет
            var skillCaster = SkillCaster.GetByType((SkillCasterType)skillCasterType);
            skillCaster.Read(stream);

            var skillCastTargetType = stream.ReadByte(); // на кого применяют
            var skillCastTarget = SkillCastTarget.GetByType((SkillCastTargetType)skillCastTargetType);
            skillCastTarget.Read(stream);

            var flag = stream.ReadByte();
            var flagType = flag & 0x3F;
            var skillObject = SkillObject.GetByType((SkillObjectType)flagType);
            skillObject.Flag40 = (flag & 0x40) != 0;
            skillObject.Flag80 = (flag & 0x80) != 0;
            if (flagType > 0)
                skillObject.Read(stream);
            skillObject.ReadInputDirection(stream);

            // AA8 casting_useable plots (for example Concussive Arrow: Flame
            // and Snipe: Lightning) may be released by pressing the same skill
            // again. Depending on the client-side input path this arrives as a
            // second StartSkill rather than CSStopCasting. Consume that second
            // request before cooldown/GCD validation and release the existing
            // plot timeline instead of constructing a second Skill instance.
            if (TryReleaseActivePlotCast(Connection.ActiveChar, skillId))
                return;

            if (skillId is 11918 or 18757 or 23587 or 40333 or 40378)
            {
                var targetDescription = skillCastTarget switch
                {
                    SkillCastPositionTarget position =>
                        $"position=<{position.PosX:F3},{position.PosY:F3},{position.PosZ:F3}> rot={position.PosRot:F3}",
                    SkillCastPosition2Target position =>
                        $"position2=<{position.PosX:F3},{position.PosY:F3},{position.PosZ:F3}> end=<{position.EndPosX:F3},{position.EndPosY:F3},{position.EndPosZ:F3}>",
                    SkillCastPosition3Target position =>
                        $"position3=<{position.PosX:F3},{position.PosY:F3},{position.PosZ:F3}> pitch={position.Pitch:F3}",
                    _ => $"objId={skillCastTarget.ObjId}"
                };

                _log.Info(
                    "[AA8Movement] CSStartSkill skill={0} casterType={1} targetType={2} {3} flag=0x{4:X2} inputDirection={5}",
                    skillId, skillCaster.Type, skillCastTarget.Type, targetDescription, flag, skillObject.InputDirection);
            }

            _log.Trace("StartSkill: Id {0}, flag {1}", skillId, flag);
            if (SkillManager.Instance.IsSkillQuarantined(skillId))
            {
                var reason = SkillManager.Instance.GetSkillQuarantineReason(skillId);
                _log.Warn(
                    "StartSkill: native AA8 skill {0} is quarantined because its dependency closure is incomplete: {1}",
                    skillId,
                    reason);
                return;
            }
            if (skillCaster is SkillCasterUnit scu)
            {
                var unit = WorldManager.Instance.GetUnit(scu.ObjId);
                if (unit is Character character)
                {
                    _log.Debug("{0} is using skill {1}", character.Name, skillId);
                }
            }

            // The client may repeat StartSkill while its local movement/plot state is
            // settling. The server cooldown is authoritative: do not create another
            // cast and, crucially, do not answer with SCSkillStarted(CooldownTime).
            // AA8 treats that failure response as a fresh hotbar lifecycle and can
            // visually restart the full cooldown.
            if (!Connection.ActiveChar.IgnoreSkillCooldowns)
            {
                var remaining = Connection.ActiveChar.Cooldowns.GetRemaining(skillId);
                if (remaining > 0)
                {
                    _log.Debug(
                        "[AA8SkillStart] Suppressed duplicate skill={0}; authoritative cooldown remaining={1}ms",
                        skillId,
                        remaining);
                    return;
                }
            }

            var skillResult = SkillResult.Success;
            Skill skill = null;
            if (SkillManager.Instance.IsDefaultSkill(skillId) || SkillManager.Instance.IsCommonSkill(skillId) && !(skillCaster is SkillItem))
            {
                skill = new Skill(SkillManager.Instance.GetSkillTemplate(skillId)); // TODO: переделать / rewrite ...
                skillResult = skill.Use(Connection.ActiveChar, skillCaster, skillCastTarget, skillObject);
            }
            else if (skillCaster is SkillItem)
            {
                var item = Connection.ActiveChar.Inventory.GetItemById(((SkillItem)skillCaster).ItemId);
                var nativeEvolutionCast =
                    skillId == 30666 &&
                    item != null &&
                    skillCastTarget is SkillCastItemTarget evolutionTarget &&
                    Connection.ActiveChar.Inventory.GetItemById(evolutionTarget.Id)
                        is EquipItem targetEquipment &&
                    ItemEvolutionRuleService.Instance
                        .GetProfile(targetEquipment.TemplateId, targetEquipment.Grade)
                        .ValidMaterialItemIds
                        .Contains(item.TemplateId);
                if (item == null ||
                    (skillId != item.Template.UseSkillId && !nativeEvolutionCast))
                    return;
                //Connection.ActiveChar.Quests.OnItemUse(item);
                skill = new Skill(SkillManager.Instance.GetSkillTemplate(skillId));
                skillResult = skill.Use(Connection.ActiveChar, skillCaster, skillCastTarget, skillObject);

                // Квест Id=2255 не вызывается результат использования предмета Id=16280, Engraved Lodestone
                // добавил вызов OnItemUse
                //Connection.ActiveChar.Inventory.Bag.GetAllItemsByTemplate(((SkillItem)skillCaster).ItemTemplateId, -1, out var items, out var count);
                if (item.Count > 0)
                    Connection.ActiveChar.Quests.OnItemUse(item);
            }
            else if (Connection.ActiveChar.Skills.Skills.ContainsKey(skillId))
            {
                var template = SkillManager.Instance.GetSkillTemplate(skillId);
                if (template == null)
                    return;
                skill = new Skill(template, Connection.ActiveChar);
                skillResult = skill.Use(Connection.ActiveChar, skillCaster, skillCastTarget, skillObject);
            }
            else if (skillId > 0 && Connection.ActiveChar.Skills.IsVariantOfSkill(skillId))
            {
                // AA8 successor skills retain the learned ability's derived level. Building the
                // selected Heir variant without its owner silently forced every successor to level 1.
                var template = SkillManager.Instance.GetSkillTemplate(skillId);
                if (template == null)
                    return;
                skill = CreateVariantSkill(template, Connection.ActiveChar);
                skillResult = skill.Use(Connection.ActiveChar, skillCaster, skillCastTarget, skillObject);
            }
            else
            {
                _log.Warn("StartSkill: Id {0}, undefined use type", skillId);
                //If its a valid skill cast it. This fixes interactions with quest items/doodads.
                var template = SkillManager.Instance.GetSkillTemplate(skillId);
                if (template == null)
                    return;
                skill = new Skill(template);
                skillResult = skill.Use(Connection.ActiveChar, skillCaster, skillCastTarget, skillObject);
            }

            if (skillResult != SkillResult.Success)
            {
                if (skillResult == SkillResult.CooldownTime)
                {
                    _log.Debug(
                        "[AA8SkillStart] Suppressed transient CooldownTime response for skill={0}; no hotbar restart packet sent",
                        skillId);
                    return;
                }

                var rejected = new SCSkillStartedPacket(
                    skillId,
                    0,
                    skillCaster,
                    skillCastTarget,
                    skill,
                    skillObject)
                {
                    RealCastTime = 0,
                    BaseCastTime = 0
                };
                rejected.SetSkillResult(skillResult);
                Connection.ActiveChar.SendPacket(rejected);
                _log.Debug(
                    "[AA8SkillStart] Rejected skill={0} result={1}; native result response sent to release client pending state",
                    skillId,
                    skillResult);
            }
        }

        private static Skill CreateVariantSkill(SkillTemplate template, Unit owner)
        {
            return new Skill(template, owner);
        }

        public static bool TryReleaseActivePlotCast(Unit unit, uint requestedSkillId)
        {
            var state = unit?.ActivePlotState;
            var activeSkill = state?.ActiveSkill;
            if (activeSkill?.Template?.Id != requestedSkillId)
                return false;

            if (!state.TryReleaseCastingUseable())
                return false;

            NativeSkillLiveTrace.RecordCastingRelease(
                activeSkill,
                unit,
                state.CastingPercent);
            return true;
        }
    }
}
