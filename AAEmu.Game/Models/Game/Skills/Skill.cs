using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

using AAEmu.Commons.Utils;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.UnitManagers;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Core.Packets;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj;
using AAEmu.Game.Models.Game.Faction;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Actions;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Models.Game.NPChar;
using AAEmu.Game.Models.Game.Skills.Effects;
using AAEmu.Game.Models.Game.Skills.Effects.Enums;
using AAEmu.Game.Models.Game.Skills.Effects.SpecialEffects;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.SkillControllers;
using AAEmu.Game.Models.Game.Skills.Static;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Skills.Utils;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.StaticValues;
using AAEmu.Game.Models.Tasks.Skills;
using AAEmu.Game.Utils;

using NLog;

namespace AAEmu.Game.Models.Game.Skills
{
    public class Skill
    {
        private static Logger _log = LogManager.GetCurrentClassLogger();

        public uint Id { get; set; }
        public SkillTemplate Template { get; set; }
        public byte Level { get; set; }
        public ushort TlId { get; set; }
        public PlotState ActivePlotState { get; set; }
        public Dictionary<uint, SkillHitType> HitTypes { get; set; }
        public BaseUnit InitialTarget { get; set; }//Temp Hack Fix. Replace this with UnitsEffected
        private bool _bypassGcd;
        public bool Cancelled { get; set; } = false;
        public Action Callback { get; set; }

        //public bool isAutoAttack;
        //public SkillTask autoAttackTask;

        public Skill()
        {
            HitTypes = new Dictionary<uint, SkillHitType>();
        }

        public Skill(SkillTemplate template, Unit owner = null)
        {
            HitTypes = new Dictionary<uint, SkillHitType>();
            Id = template.Id;
            Template = template;
            if (owner != null)
                Level = template.LevelStep > 0 ? (byte)((owner.GetAbLevel((AbilityType)template.AbilityId) - template.AbilityLevel) / template.LevelStep + 1) : (byte)1;
            else
                Level = 1;
        }

        public SkillResult Use(Unit caster, SkillCaster casterCaster, SkillCastTarget targetCaster, SkillObject skillObject = null, bool bypassGcd = false)
        {
            _bypassGcd = bypassGcd;
            if (!_bypassGcd)
            {
                lock (caster.GCDLock)
                {
                    if (caster.SkillLastUsed.AddMilliseconds(150) > DateTime.UtcNow)
                        return SkillResult.CooldownTime;

                    if (caster.GlobalCooldown >= DateTime.UtcNow && !Template.IgnoreGlobalCooldown)
                        return SkillResult.CooldownTime;

                    caster.SkillLastUsed = DateTime.UtcNow;
                }
            }

            if (Template.CancelOngoingBuffs)
                caster.Buffs.TriggerRemoveOn(Buffs.BuffRemoveOn.StartSkill, Template.CancelOngoingBuffExceptionTagId);

            if (skillObject == null)
            {
                skillObject = new SkillObject();
            }

            var target = GetInitialTarget(caster, casterCaster, targetCaster);
            InitialTarget = target;
            if (target == null)
                return SkillResult.NoTarget;//We should try to make sure this doesnt happen

            TlId = SkillManager.Instance.NextId();
            if (Template.Plot != null)
            {
                Task.Run(() => Template.Plot.Run(caster, casterCaster, target, targetCaster, skillObject, this));
                if (Template.PlotOnly)
                    return SkillResult.Success;
            }

            var skillRange = caster.ApplySkillModifiers(this, SkillAttribute.Range, Template.MaxRange);
            var targetDist = caster.GetDistanceTo(target, true);
            if (!(target is Doodad)) // HACKFIX : Used mostly for boats, since the actual position of the doodad is the boat's origin, and not where it is displayed
            {
                if (targetDist < Template.MinRange)
                    return SkillResult.TooCloseRange;
                if (targetDist > skillRange)
                    return SkillResult.TooFarRange;
            }

            if (Template.WeaponSlotForRangeId > 0)
            {
                var minWeaponRange = 0.0f; // Fist default
                var maxWeaponRange = 3.0f; // Fist default
                if (caster.Equipment.GetItemBySlot(Template.WeaponSlotForRangeId)?.Template is WeaponTemplate weaponTemplate)
                {
                    minWeaponRange = weaponTemplate.HoldableTemplate.MinRange;
                    maxWeaponRange = weaponTemplate.HoldableTemplate.MaxRange;
                }

                if (targetDist < minWeaponRange)
                    return SkillResult.TooCloseRange;
                if (targetDist > maxWeaponRange)
                    return SkillResult.TooFarRange;
            }

            if (Template.CastingTime > 0)
            {
                // var origTime = Template.CastingTime * caster.Cas
                var castTime = (int)(caster.CastTimeMul * caster.SkillModifiersCache.ApplyModifiers(this, SkillAttribute.CastTime, Template.CastingTime));

                if (caster is Character chara)
                {
                }

                if (castTime < 0)
                    castTime = 0;

                caster.BroadcastPacket(new SCSkillStartedPacket(Id, TlId, casterCaster, targetCaster, this, skillObject)
                {
                    RealCastTime = castTime,
                    BaseCastTime = Template.CastingTime
                }, true);

                caster.SkillTask = new CastTask(this, caster, casterCaster, target, targetCaster, skillObject);
                TaskManager.Instance.Schedule(caster.SkillTask, TimeSpan.FromMilliseconds(castTime));
            }
            // else if (caster is Character && (Id == 2 || Id == 3 || Id == 4) && !caster.IsAutoAttack)
            // {
            //     caster.IsAutoAttack = true; // enable auto attack
            //     caster.SkillId = Id;
            //     caster.TlId = TlId;
            //     caster.BroadcastPacket(new SCSkillStartedPacket(Id, 0, casterCaster, targetCaster, this, skillObject)
            //     {
            //         CastTime = Template.CastingTime
            //     }, true);
            //
            //     caster.AutoAttackTask = new MeleeCastTask(this, caster, casterCaster, target, targetCaster, skillObject);
            //     TaskManager.Instance.Schedule(caster.AutoAttackTask, TimeSpan.FromMilliseconds(300), TimeSpan.FromMilliseconds(1300));
            // }
            else
            {
                Cast(caster, casterCaster, target, targetCaster, skillObject);
            }

            return SkillResult.Success;
        }

        private BaseUnit GetInitialTarget(Unit caster, SkillCaster skillCaster, SkillCastTarget targetCaster)
        {
            var target = (BaseUnit)caster;
            if (target == null) // проверяем, так как иногда бывает null
            {
                return null;
            }
            // HACKFIX : Mounts and Turbulence
            if (skillCaster.Type == SkillCasterType.Unk3 || caster == null && skillCaster.Type == SkillCasterType.Unit)
                target = WorldManager.Instance.GetUnit(skillCaster.ObjId);

            if (Template.TargetType == SkillTargetType.Self)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    targetCaster.ObjId = target.ObjId;
                }
            }
            else if (Template.TargetType == SkillTargetType.Friendly)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }

                if (caster.GetRelationStateTo(target) != RelationState.Friendly)
                {
                    return null; //TODO отправлять ошибку?
                }
            }
            else if (Template.TargetType == SkillTargetType.Hostile)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }

                if (caster.GetRelationStateTo(target) != RelationState.Hostile)
                {
                    if (!caster.CanAttack(target))
                    {
                        return null; //TODO отправлять ошибку?
                    }
                }
            }
            else if (Template.TargetType == SkillTargetType.AnyUnit)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }
            }
            else if (Template.TargetType == SkillTargetType.Doodad)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }
            }
            else if (Template.TargetType == SkillTargetType.Item)
            {
                // TODO ...
            }
            else if (Template.TargetType == SkillTargetType.Others)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }

                if (caster.ObjId == target.ObjId)
                {
                    return null; //TODO отправлять ошибку?
                }
            }
            else if (Template.TargetType == SkillTargetType.FriendlyOthers)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }

                if (caster.ObjId == target.ObjId)
                {
                    return null; //TODO отправлять ошибку?
                }
                if (caster.GetRelationStateTo(target) != RelationState.Friendly)
                {
                    return null; //TODO отправлять ошибку?
                }
            }
            else if (Template.TargetType == SkillTargetType.Building)
            {
                if (targetCaster.Type == SkillCastTargetType.Unit || targetCaster.Type == SkillCastTargetType.Doodad)
                {
                    target = targetCaster.ObjId > 0 ? WorldManager.Instance.GetBaseUnit(targetCaster.ObjId) : caster;
                    targetCaster.ObjId = target.ObjId;
                }

                if (caster.ObjId == target.ObjId)
                {
                    return null; //TODO отправлять ошибку?
                }
            }
            else if (Template.TargetType == SkillTargetType.Pos)
            {
                var positionTarget = (SkillCastPositionTarget)targetCaster;
                var positionUnit = new BaseUnit();
                positionUnit.ObjId = uint.MaxValue;
                positionUnit.Transform = caster.Transform.CloneDetached(positionUnit);
                positionUnit.Transform.Local.SetPosition(positionTarget.PosX, positionTarget.PosY, positionTarget.PosZ);
                positionUnit.Region = caster.Region;
                target = positionUnit;
            }
            else if (Template.TargetType == SkillTargetType.BallisticPos)
            {
                var positionTarget = (SkillCastPositionTarget)targetCaster;
                var positionUnit = new BaseUnit();
                positionUnit.ObjId = uint.MaxValue;
                positionUnit.Transform = caster.Transform.CloneDetached(positionUnit);
                positionUnit.Transform.Local.SetPosition(positionTarget.PosX, positionTarget.PosY, positionTarget.PosZ);
                positionUnit.Region = caster.Region;
                target = positionUnit;
            }

            return target;
        }

        public void Cast(Unit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject)
        {
            if (!_bypassGcd)
            {
                var gcd = Template.CustomGcd;
                if (Template.DefaultGcd)
                    gcd = caster is NPChar.Npc ? 1500 : 1000;

                caster.GlobalCooldown = DateTime.UtcNow.AddMilliseconds(gcd * (caster.GlobalCooldownMul / 100));
            }
            if (Template.EndSkillController)
                caster.ActiveSkillController?.End();

            if (Template.SkillControllerId != 0 && target != null)
            {
                var scTemplate = SkillManager.Instance.GetEffectTemplate(Template.SkillControllerId, "SkillController") as SkillControllerTemplate;

                // Get a random number (from 0 to n)
                var value = Rand.Next(0, 1);
                // для skillId = 2
                // 87 (35) - удар наотмаш, chr
                //  2 (00) - удар сбоку, NPC
                //  3 (46) - удар сбоку, chr
                //  1 (00) - удар похож на 2 удар сбоку, NPC
                // 91 - удар сверху (немного справа)
                // 92 - удар наотмашь слева вниз направо
                //  0 - удар не наносится (расстояние большое и надо подойти поближе), f=1, c=15
                var effectDelay = new Dictionary<int, short> { { 0, 46 }, { 1, 35 } };
                var fireAnimId = new Dictionary<int, int> { { 0, 3 }, { 1, 87 } };
                var effectDelay2 = new Dictionary<int, short> { { 0, 0 }, { 1, 0 } };
                var fireAnimId2 = new Dictionary<int, int> { { 0, 1 }, { 1, 2 } };

                var dist = MathUtil.CalculateDistance(caster.Transform.World.Position, target.Transform.World.Position, true);
                if (Id == 23587)
                {
                    _log.Info(
                        "[AA8Movement] DirectSkillController skill={0} controller={1} found={2} kind={3} caster={4} target={5} distance={6:F3} range={7:F3}-{8:F3}",
                        Id, Template.SkillControllerId, scTemplate != null, scTemplate?.KindId ?? 0, caster.ObjId,
                        target.ObjId, dist, Template.MinRange, Template.MaxRange);
                }
                if (dist >= SkillManager.Instance.GetSkillTemplate(Id).MinRange && dist <= SkillManager.Instance.GetSkillTemplate(Id).MaxRange)
                {

                    var sc = SkillController.CreateSkillController(scTemplate, caster, target);
                    if (sc != null)
                    {
                        if (caster.ActiveSkillController != null)
                            caster.ActiveSkillController.End();
                        caster.ActiveSkillController = sc;
                        sc.Execute();
                        if (Id == 23587)
                            _log.Info("[AA8Movement] DirectSkillController started skill={0} controller={1}", Id,
                                Template.SkillControllerId);
                    }
                }
            }
            caster.SkillTask = null;

            ConsumeMana(caster);
            caster.Cooldowns.AddCooldown(Template.Id, (uint)Template.CooldownTime);

            // if (Id == 2 || Id == 3 || Id == 4)
            // {
            //     if (caster is Character && caster.CurrentTarget == null)
            //     {
            //         StopSkill(caster);
            //         return;
            //     }
            //
            //     // Get a random number (from 0 to n)
            //     var value = Rand.Next(0, 1);
            //     // для skillId = 2
            //     // 87 (35) - удар наотмаш, chr
            //     //  2 (00) - удар сбоку, NPC
            //     //  3 (46) - удар сбоку, chr
            //     //  1 (00) - удар похож на 2 удар сбоку, NPC
            //     // 91 - удар сверху (немного справа)
            //     // 92 - удар наотмашь слева вниз направо
            //     //  0 - удар не наносится (расстояние большое и надо подойти поближе), f=1, c=15
            //     var effectDelay = new Dictionary<int, short> { { 0, 46 }, { 1, 35 } };
            //     var fireAnimId = new Dictionary<int, int> { { 0, 3 }, { 1, 87 } };
            //     var effectDelay2 = new Dictionary<int, short> { { 0, 0 }, { 1, 0 } };
            //     var fireAnimId2 = new Dictionary<int, int> { { 0, 1 }, { 1, 2 } };
            //
            //     var trg = (Unit)target;
            //     var dist = MathUtil.CalculateDistance(caster.Position, trg.Position, true);
            //     if (dist >= SkillManager.Instance.GetSkillTemplate(Id).MinRange && dist <= SkillManager.Instance.GetSkillTemplate(Id).MaxRange)
            //     {
            //         caster.BroadcastPacket(caster is Character
            //                 ? new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject, effectDelay[value], fireAnimId[value])
            //                 : new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject, effectDelay2[value], fireAnimId2[value]),
            //             true);
            //     }
            //     else
            //     {
            //         caster.BroadcastPacket(caster is Character
            //                 ? new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject, effectDelay[value], fireAnimId[value], false)
            //                 : new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject, effectDelay2[value], fireAnimId2[value], false),
            //             true);
            //
            //         if (caster is Character chr)
            //         {
            //             chr.SendMessage("Target is too far ...");
            //         }
            //         return;
            //     }
            // }

            // Validate cast Item
            if (caster is Character player && casterCaster is SkillItem castItem)
            {
                var castItemTemplate = ItemManager.Instance.GetTemplate(castItem.ItemTemplateId);
                if (castItemTemplate.UseSkillAsReagent)
                {
                    var useItem = ItemManager.Instance.GetItemByItemId(castItem.ItemId);
                    if (useItem == null)
                    {
                        _log.Warn("SkillItem does not exists {0} (templateId: {1})", castItem.ItemId, castItem.ItemTemplateId);
                        return; // Item does not exists
                    }

                    if (useItem._holdingContainer.Owner.Id != player.Id)
                    {
                        _log.Warn("SkillItem {0} (itemId:{1}) is not owned by player {2} ({3})", useItem.Template.Name, useItem.Id, player.Name, player.Id);
                        return; // Item is not in the player's possessions
                    }

                    var itemCount = player.Inventory.GetItemsCount(useItem.TemplateId);
                    var itemsRequired = 1; // TODO: This probably needs a check if it doesn't require multiple of source item to use, instead of just 1
                    if (itemCount < itemsRequired)
                    {
                        _log.Warn("SkillItem, player does not own enough of {0} (count: {1}/{2}, templateId: {3})", useItem.Id, itemCount, itemsRequired, castItem.ItemTemplateId);
                        return; // not enough of item
                    }
                }
            }

            if (Template.ChannelingTime > 0)
            {
                StartChanneling(caster, casterCaster, target, targetCaster, skillObject);
            }
            else
            {
                ScheduleEffects(caster, casterCaster, target, targetCaster, skillObject);
            }

        }

        public async void StopSkill(Unit caster)
        {
            await caster.AutoAttackTask.Cancel();
            caster.BroadcastPacket(new SCSkillEndedPacket(TlId), true);
            caster.BroadcastPacket(new SCSkillStoppedPacket(caster.ObjId, Id), true);
            caster.AutoAttackTask = null;
            caster.IsAutoAttack = false; // turned off auto attack
            SkillManager.Instance.ReleaseId(TlId);
        }

        public void StartChanneling(Unit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject)
        {
            if (Template.ChannelingBuffId != 0)
            {
                var buff = SkillManager.Instance.GetBuffTemplate(Template.ChannelingBuffId);
                buff.Apply(caster, casterCaster, target, targetCaster, new CastSkill(Template.Id, TlId), new EffectSource(this), skillObject, DateTime.UtcNow);
            }

            if (Template.ChannelingTargetBuffId != 0)
            {
                var buff = SkillManager.Instance.GetBuffTemplate(Template.ChannelingTargetBuffId);
                buff.Apply(caster, casterCaster, target, targetCaster, new CastSkill(Template.Id, TlId), new EffectSource(this), skillObject, DateTime.UtcNow);
            }

            Doodad doodad = null;
            if (Template.ChannelingDoodadId > 0)
            {
                doodad = DoodadManager.Instance.Create(0, Template.ChannelingDoodadId, caster);
                doodad.Transform = caster.Transform.CloneDetached(doodad);
                doodad.Spawn();
            }

            var fireAnimId = ResolveFireAnimId(caster);
            caster.BroadcastPacket(new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject,
                fireAnimId), true);
            caster.SkillTask = new EndChannelingTask(this, caster, casterCaster, target, targetCaster, skillObject, doodad);
            TaskManager.Instance.Schedule(caster.SkillTask, TimeSpan.FromMilliseconds(Template.ChannelingTime));
        }

        public void EndChanneling(Unit caster, Doodad channelDoodad)
        {
            caster.SkillTask = null;
            if (Template.ChannelingBuffId != 0)
            {
                caster.Buffs.RemoveEffect(Template.ChannelingBuffId, Template.Id);
            }
            if (Template.ChannelingTargetBuffId != 0)
            {
                InitialTarget.Buffs.RemoveEffect(Template.ChannelingTargetBuffId, Template.Id);
            }

            channelDoodad?.Delete();

            EndSkill(caster);

            caster.Events.OnChannelingCancel(this, new OnChannelingCancelArgs());
        }

        public void ScheduleEffects(Unit caster, SkillCaster casterCaster, BaseUnit target, SkillCastTarget targetCaster, SkillObject skillObject)
        {
            if (Template.ToggleBuffId != 0)
            {
                var buff = SkillManager.Instance.GetBuffTemplate(Template.ToggleBuffId);
                buff.Apply(caster, casterCaster, target, targetCaster, new CastSkill(Template.Id, TlId), new EffectSource(this), skillObject, DateTime.UtcNow);
            }

            var totalDelay = 0;
            if (Template.EffectDelay > 0)
                totalDelay += Template.EffectDelay;
            if (Template.EffectSpeed > 0)
                totalDelay += (int)(caster.GetDistanceTo(target) / Template.EffectSpeed * 1000.0f);
            var fireAnimId = ResolveFireAnimId(caster);
            var fireAnim = AnimationManager.Instance.GetAnimation(fireAnimId);
            if (fireAnim != null && Template.UseAnimTime)
                totalDelay += (int)(fireAnim.CombatSyncTime * (caster.GlobalCooldownMul / 100));


            caster.BroadcastPacket(new SCSkillFiredPacket(Id, TlId, casterCaster, targetCaster, this, skillObject,
                fireAnimId)
            {
                ComputedDelay = (short)totalDelay
            }, true);

            if (totalDelay > 0)
            {
                var thisSkillTask = new ApplySkillTask(this, caster, casterCaster, target, targetCaster, skillObject);
                TaskManager.Instance.Schedule(thisSkillTask, TimeSpan.FromMilliseconds(totalDelay));
            }
            else
            {
                ApplyEffects(caster, casterCaster, target, targetCaster, skillObject);
                EndSkill(caster);
            }
        }

        /// <summary>
        /// Selects the native AA8 fire-animation variant for the caster's
        /// current weapon layout. Missing variants fall back to the skill's
        /// base animation instead of substituting historical data.
        /// </summary>
        public uint ResolveFireAnimId(Unit caster)
        {
            if (caster is Character character)
                return SelectFireAnimId(character.GetWeaponWieldKind(), Template.FireAnimId,
                    Template.TwohandFireAnimId, Template.DualWieldFireAnimId);

            return Template.FireAnimId;
        }

        public static uint SelectFireAnimId(WeaponWieldKind wieldKind, uint baseAnimId, uint twohandAnimId,
            uint dualWieldAnimId)
        {
            switch (wieldKind)
            {
                case WeaponWieldKind.TwoHanded when twohandAnimId != 0:
                    return twohandAnimId;
                case WeaponWieldKind.DuelWielded when dualWieldAnimId != 0:
                    return dualWieldAnimId;
                default:
                    return baseAnimId;
            }
        }

        private IEnumerable<BaseUnit> FilterAoeUnits(BaseUnit caster, IEnumerable<BaseUnit> units)
        {
            units = SkillTargetingUtil.FilterWithRelation(Template.TargetRelation, caster, units);
            return units;
        }

        public void ApplyEffects(Unit caster, SkillCaster casterCaster, BaseUnit targetSelf, SkillCastTarget targetCaster, SkillObject skillObject)
        {
            // Kakao AA8 Gear Upgrade does not use the reagent's ordinary
            // right-click semantics when inserting a socket. It sends the
            // same item skill with an item target and SkillObject type 10.
            // x2game.dll FUN_39121470 and FUN_399af960 confirm that context
            // and its autoUseAAPoint/count/continuous payload.
            if (skillObject is SkillObjectSocketInstallOptions socketOptions &&
                casterCaster is SkillItem socketReagent &&
                targetCaster is SkillCastItemTarget &&
                ItemSocketRuleService.Instance.GetDefinition(
                    socketReagent.ItemTemplateId)?.Kind ==
                ItemSocketDefinitionKind.Lunagem)
            {
                new ItemSocketing().ExecuteNativeSocketContext(
                    caster,
                    casterCaster,
                    targetCaster,
                    this,
                    socketOptions);
                return;
            }

            var targets = new List<BaseUnit>(); // TODO crutches
            if (Template.TargetAreaRadius > 0)
            {
                var units = WorldManager.Instance.GetAround<BaseUnit>(targetSelf, Template.TargetAreaRadius, true);
                units.Add(targetSelf);
                units = FilterAoeUnits(caster, units).ToList();

                targets.AddRange(units);
                // TODO : Need to this if this is needed
                //if (targetSelf is Unit) targets.Add(targetSelf);
            }
            else
            {
                targets.Add(targetSelf);
            }

            foreach (var target in targets)
            {
                if (target is Unit trg && Template.TargetType == SkillTargetType.Hostile)
                {
                    HitTypes.TryAdd(trg.ObjId, RollCombatDice(caster, trg));
                }
                if (target is Doodad doodad)
                {
                    doodad.OnSkillHit(caster, Id);
                }
            }

            var packets = new CompressedGamePackets();
            var consumedItems = new List<(Item, int)>();
            var consumedItemTemplates = new List<(uint, int)>(); // itemTemplateId, amount

            var effectsToApply = new List<(BaseUnit target, SkillEffect effect)>(targets.Count * Template.Effects.Count);
            foreach (var effect in Template.Effects)
            {
                var effectedTargets = new List<BaseUnit>();
                switch (effect.ApplicationMethod)
                {
                    case SkillEffectApplicationMethod.Target:
                        effectedTargets = targets;//keep target
                        break;
                    case SkillEffectApplicationMethod.Source:
                        effectedTargets.Add(caster);//Diff between Source and SourceOnce?
                        break;
                    case SkillEffectApplicationMethod.SourceOnce:
                        // TODO: HACKFIX for owner's mark
                        if (casterCaster.Type == SkillCasterType.Unk3 && targetSelf is Slave)
                            effectedTargets = targets;
                        else
                            effectedTargets.Add(caster);//idk
                        break;
                    case SkillEffectApplicationMethod.SourceToPos:
                        effectedTargets = targets;
                        break;
                }

                foreach (var target in effectedTargets)
                {
                    var relationState = caster.GetRelationStateTo(target);
                    if (effect.StartLevel > caster.Level || effect.EndLevel < caster.Level)
                    {
                        continue;
                    }

                    if (effect.Friendly && !effect.NonFriendly && relationState != RelationState.Friendly)
                    {
                        continue;
                    }

                    if (!effect.Friendly && effect.NonFriendly && relationState != RelationState.Hostile)
                    {
                        if (relationState == RelationState.Friendly && !caster.ForceAttack || caster.ObjId == target.ObjId)
                        {
                            continue;
                        }
                    }

                    if (effect.Front && !effect.Back && !MathUtil.IsFront(caster, target))
                    {
                        continue;
                    }

                    if (!effect.Front && effect.Back && MathUtil.IsFront(caster, target))
                    {
                        continue;
                    }

                    if (effect.SourceBuffTagId > 0 && !caster.Buffs.CheckBuffs(SkillManager.Instance.GetBuffsByTagId(effect.SourceBuffTagId)))
                    {
                        continue;
                    }

                    if (effect.SourceNoBuffTagId > 0 && caster.Buffs.CheckBuffs(SkillManager.Instance.GetBuffsByTagId(effect.SourceNoBuffTagId)))
                    {
                        continue;
                    }

                    if (effect.TargetBuffTagId > 0 && !target.Buffs.CheckBuffs(SkillManager.Instance.GetBuffsByTagId(effect.TargetBuffTagId)))
                    {
                        continue;
                    }

                    if (effect.TargetNoBuffTagId > 0 && target.Buffs.CheckBuffs(SkillManager.Instance.GetBuffsByTagId(effect.TargetNoBuffTagId)))
                    {
                        continue;
                    }

                    if (effect.Chance < 100 && Rand.Next(100) > effect.Chance)
                    {
                        continue;
                    }

                    if (casterCaster is SkillItem castItem && caster is Character player)
                    {
                        var useItem = ItemManager.Instance.GetItemByItemId(castItem.ItemId);
                        if (effect.ConsumeSourceItem)
                            consumedItems.Add((useItem, effect.ConsumeItemCount));
                        //player.Inventory.Bag.ConsumeItem(ItemTaskType.SkillReagents, castItem.ItemTemplateId, effect.ConsumeItemCount, useItem);
                        else
                        {
                            var castItemTemplate = ItemManager.Instance.GetTemplate(castItem.ItemTemplateId);
                            if (castItemTemplate.UseSkillAsReagent)
                                consumedItems.Add((useItem, effect.ConsumeItemCount));
                            //player.Inventory.Bag.ConsumeItem(ItemTaskType.SkillReagents, castItemTemplate.Id, effect.ConsumeItemCount, useItem);
                        }
                    }

                    if (caster is Character character && effect.ConsumeItemId != 0 && effect.ConsumeItemCount > 0)
                    {
                        if (effect.ConsumeSourceItem)
                        {
                            if (!character.Inventory.Bag.AcquireDefaultItem(ItemTaskType.SkillEffectConsumption,
                                effect.ConsumeItemId, effect.ConsumeItemCount))
                                continue;
                        }
                        else
                        {
                            var inventory = character.Inventory.CheckItems(SlotType.Inventory, effect.ConsumeItemId, effect.ConsumeItemCount);
                            var equipment = character.Inventory.CheckItems(SlotType.Equipment, effect.ConsumeItemId, effect.ConsumeItemCount);
                            if (!(inventory || equipment))
                            {
                                continue;
                            }

                            consumedItemTemplates.Add((effect.ConsumeItemId, effect.ConsumeItemCount));
                            /*
                            if (inventory)
                                character.Inventory.Bag.ConsumeItem(ItemTaskType.SkillEffectConsumption, effect.ConsumeItemId, effect.ConsumeItemCount, null);
                            else
                            if (equipment)
                                character.Inventory.Equipment.ConsumeItem(ItemTaskType.SkillEffectConsumption, effect.ConsumeItemId, effect.ConsumeItemCount, null);
                            */
                        }
                    }

                    effectsToApply.Add((target, effect));
                    //effect.Template?.Apply(caster, casterCaster, target, targetCaster, new CastSkill(Template.Id, TlId), new EffectSource(this), skillObject, DateTime.UtcNow, packets);
                }
            }

            //This will handle all items with a reagent/product
            var reagents = SkillManager.Instance.GetSkillReagentsBySkillId(Template.Id);
            var skillProducts = SkillManager.Instance.GetSkillProductsBySkillId(Template.Id);
            if (reagents != null && skillProducts != null)
            {
                if (caster is Character player)
                {
                    if (reagents.Count > 0)
                    {
                        foreach (var reagent in reagents)
                        {
                            var consumeCount = player.Inventory.Bag.ConsumeItem(ItemTaskType.SkillReagents, reagent.ItemId, reagent.Amount, null);
                            if (consumeCount < reagent.Amount)
                            {
                                player.Inventory.Equipment.ConsumeItem(ItemTaskType.SkillReagents, reagent.ItemId, reagent.Amount, null);
                            }
                        }
                    }

                    if (skillProducts.Count > 0)
                    {
                        foreach (var product in skillProducts)
                        {
                            player.Inventory.Bag.AcquireDefaultItem(ItemTaskType.SkillEffectGainItem, product.ItemId, product.Amount);
                        }
                    }
                }
            }
            else
                _log.Error("Could not find Reagents/Products for Template[{0}", Template.Id);

            foreach (var item in effectsToApply)
            {
                //Template can be null for some reason..
                if (item.effect.Template != null)
                    item.effect.Template.Apply(caster, casterCaster, item.target, targetCaster, new CastSkill(Template.Id, TlId), new EffectSource(this), skillObject, DateTime.UtcNow, packets);
                else
                    _log.Error("Template not found for Skill[{0}] Effect[{1}]", Template.Id, item.effect.EffectId);
            }

            // Quick Hack
            if (packets.Packets.Count > 0)
                caster.BroadcastPacket(packets, true);

            if (!Cancelled)
            {
                // Actually consume the to be consumed items
                foreach (var (item, amount) in consumedItems)
                    if (item._holdingContainer != null)
                    {
                        item._holdingContainer.ConsumeItem(ItemTaskType.SkillReagents, item.TemplateId, amount, item);
                    }

                if (caster is Character playerToConsumeFrom)
                    foreach (var (templateId, amount) in consumedItemTemplates)
                        playerToConsumeFrom.Inventory.ConsumeItem(null, ItemTaskType.SkillEffectConsumption, templateId, amount, null);
            }
        }

        public void EndSkill(Unit caster)
        {
            if (Template.ConsumeLaborPower > 0 && caster is Character chart && !Cancelled)
            {
                // Consume labor
                chart.ChangeLabor((short)-Template.ConsumeLaborPower, Template.ActabilityGroupId);

                // Add vocation where needed
                if (InitialTarget is Doodad doodad && caster is Character character)
                {
                    if (doodad.Template.GrantsVocationWhenUsed())
                    {
                        // From what I remember this has always been half the labor rounded upwards
                        // This is however not correct, as some actions only give a fraction of what you would normally expect
                        // We multiply the BASE value for server settings, not the total (although I don't think this would affect anything since we don't really have a +1 badge/action buff)
                        character.ChangeGamePoints(GamePointKind.Vocation, (int)Math.Ceiling(AppConfiguration.Instance.World.VocationRate * Template.ConsumeLaborPower / 2));
                    }
                }
            }

            Callback?.Invoke();
            caster.OnSkillEnd(this);
            caster.BroadcastPacket(new SCSkillEndedPacket(TlId), true);
            SkillManager.Instance.ReleaseId(TlId);

            if (caster is Character character1 && character1.IgnoreSkillCooldowns)
                character1.ResetSkillCooldown(Template.Id, false);
        }

        public void Stop(Unit caster, Doodad channelDoodad = null)
        {
            if (Template.ChannelingTime > 0)
            {
                EndChanneling(caster, channelDoodad);
            }

            if (Template.ToggleBuffId != 0)
            {
                caster.Buffs.RemoveEffect(Template.ToggleBuffId, Template.Id);
            }
            caster.BroadcastPacket(new SCCastingStoppedPacket(TlId, 0), true);
            caster.BroadcastPacket(new SCSkillEndedPacket(TlId), true);
            Callback?.Invoke();
            caster.OnSkillEnd(this);
            caster.SkillTask = null;
            Cancelled = true;
            SkillManager.Instance.ReleaseId(TlId);

            if (caster is Character character && character.IgnoreSkillCooldowns)
                character.ResetSkillCooldown(Template.Id, false);
            //TlId = 0;
        }

        public SkillHitType RollCombatDice(Unit attacker, Unit target)
        {
            // TODO
            //  -Calculate Hit/Miss Rates
            //  -Check for AlwaysHit?
            //  -Only Parry if sword equipped?
            var damageType = (DamageType)Template.DamageTypeId;
            var bullsEyeMod = attacker.BullsEye / 1000f * 3f / 100f;
            var combatStats = CombatStatOverrideManager.Instance;
            var trace = combatStats.ShouldTrace(attacker) || combatStats.ShouldTrace(target);
            var relativeFrontAngle = MathUtil.CalculateRelativeAngle(target, attacker);
            var isFront = Math.Abs(relativeFrontAngle) <= 90.0;

            //TODO Check immmunity a better way!!!
            //if (target.Buffs.CheckBuffs(SkillManager.Instance.GetBuffsByTagId(361)))
            //return SkillHitType.Immune;

            //Idk if this is right. Double check it
            if (!isFront)
            {
                if (trace)
                    _log.Debug(
                        "AA8CombatDice skill={0} attacker={1} target={2} damageType={3} front=false relativeAngle={4:0.###} defenderYaw={5:0.###} defensiveRolls=skipped",
                        Template.Id,
                        attacker.ObjId,
                        target.ObjId,
                        damageType,
                        relativeFrontAngle,
                        target.Transform.World.Rotation.Z.RadToDeg());
                goto AlwaysHit;
            }

            var dodgeRate = combatStats.Resolve(
                target,
                CombatStatKind.Dodge,
                target.DodgeRate);
            var dodgeRoll = Rand.Next(0f, 100f);
            if (dodgeRoll < dodgeRate - bullsEyeMod)
            {
                if (damageType == DamageType.Melee)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "dodge", dodgeRate, dodgeRoll, SkillHitType.MeleeDodge);
                    return SkillHitType.MeleeDodge;
                }
                else if (damageType == DamageType.Ranged)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "dodge", dodgeRate, dodgeRoll, SkillHitType.RangedDodge);
                    return SkillHitType.RangedDodge;
                }
            }

            var blockRate = combatStats.Resolve(
                target,
                CombatStatKind.Block,
                target.BlockRate);
            var blockRoll = Rand.Next(0f, 100f);
            if (blockRoll < blockRate - bullsEyeMod)
            {
                if (damageType == DamageType.Melee)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "block", blockRate, blockRoll, SkillHitType.MeleeBlock);
                    return SkillHitType.MeleeBlock;
                }
                else if (damageType == DamageType.Ranged)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "block", blockRate, blockRoll, SkillHitType.RangedBlock);
                    return SkillHitType.RangedBlock;
                }
            }

            var meleeParryRate = combatStats.Resolve(
                target,
                CombatStatKind.MeleeParry,
                target.MeleeParryRate);
            var meleeParryRoll = Rand.Next(0f, 100f);
            if (meleeParryRoll < meleeParryRate - bullsEyeMod)
            {
                if (damageType == DamageType.Melee)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "meleeParry", meleeParryRate, meleeParryRoll, SkillHitType.MeleeParry);
                    return SkillHitType.MeleeParry;
                }
                if (damageType == DamageType.Ranged
                    && CanParryRangedAttack(
                        target.Buffs.CheckBuff((uint)BuffConstants.WeaponTraining),
                        target.Buffs.CheckBuff((uint)BuffConstants.EquipDualwield),
                        target.Buffs.CheckBuff((uint)BuffConstants.EquipTwoHanded)))
                {
                    TraceCombatDice(trace, attacker, target, damageType, "meleeParry", meleeParryRate, meleeParryRoll, SkillHitType.MeleeParry);
                    return SkillHitType.MeleeParry;
                }
            }

            var rangedParryRate = combatStats.Resolve(
                target,
                CombatStatKind.RangedParry,
                target.RangedParryRate);
            var rangedParryRoll = Rand.Next(0f, 100f);
            if (rangedParryRoll < rangedParryRate - bullsEyeMod)
            {
                if (damageType == DamageType.Ranged)
                {
                    TraceCombatDice(trace, attacker, target, damageType, "rangedParry", rangedParryRate, rangedParryRoll, SkillHitType.RangedParry);
                    return SkillHitType.RangedParry;
                }
            }

AlwaysHit:
            float accuracy;
            float accuracyRoll;
            SkillHitType result;
            switch (damageType)
            {
                case DamageType.Melee:
                    accuracy = combatStats.Resolve(
                        attacker,
                        CombatStatKind.MeleeAccuracy,
                        attacker.MeleeAccuracy);
                    accuracyRoll = Rand.Next(0f, 100f);
                    result = accuracyRoll < accuracy ? SkillHitType.MeleeHit : SkillHitType.MeleeMiss;
                    break;
                case DamageType.Magic:
                    accuracy = combatStats.Resolve(
                        attacker,
                        CombatStatKind.SpellAccuracy,
                        attacker.SpellAccuracy);
                    accuracyRoll = Rand.Next(0f, 100f);
                    result = accuracyRoll < accuracy ? SkillHitType.SpellHit : SkillHitType.SpellMiss;
                    break;
                case DamageType.Ranged:
                    accuracy = combatStats.Resolve(
                        attacker,
                        CombatStatKind.RangedAccuracy,
                        attacker.RangedAccuracy);
                    accuracyRoll = Rand.Next(0f, 100f);
                    result = accuracyRoll < accuracy ? SkillHitType.RangedHit : SkillHitType.RangedMiss;
                    break;
                case DamageType.Siege:
                    return SkillHitType.RangedHit;//No siege type?
                default:
                    return SkillHitType.Invalid;
            }

            TraceCombatDice(trace, attacker, target, damageType, "accuracy", accuracy, accuracyRoll, result);
            return result;
        }

        public static bool CanParryRangedAttack(
            bool hasWeaponTraining,
            bool hasDualWield,
            bool hasTwoHandedWeapon)
        {
            return hasWeaponTraining && (hasDualWield || hasTwoHandedWeapon);
        }

        private void TraceCombatDice(
            bool trace,
            Unit attacker,
            Unit target,
            DamageType damageType,
            string check,
            float rate,
            float roll,
            SkillHitType result)
        {
            if (!trace)
                return;

            _log.Debug(
                "AA8CombatDice skill={0} attacker={1} target={2} damageType={3} check={4} rate={5:0.###} roll={6:0.###} result={7}",
                Template.Id,
                attacker.ObjId,
                target.ObjId,
                damageType,
                check,
                rate,
                roll,
                result);
        }

        public bool SkillMissed(uint objId)
        {
            if (HitTypes.TryGetValue(objId, out var hitType))
            {
                return hitType == SkillHitType.MeleeDodge
                    || hitType == SkillHitType.MeleeParry
                    || hitType == SkillHitType.MeleeBlock
                    || hitType == SkillHitType.MeleeMiss
                    || hitType == SkillHitType.RangedDodge
                    || hitType == SkillHitType.RangedParry
                    || hitType == SkillHitType.RangedBlock
                    || hitType == SkillHitType.RangedMiss
                    || hitType == SkillHitType.Immune;
            }
            _log.Error($"Unit[{objId}] was not found in the CbtDiceRolls.");
            return true;
        }

        public void ConsumeMana(Unit caster)
        {
            var baseCost = ((caster.GetAbLevel((AbilityType)Template.AbilityId) - 1) * 1.6 + 8) * 3 / 3.65;
            var cost2 = baseCost * Template.ManaLevelMd + Template.ManaCost;
            var manaCost = (int)caster.SkillModifiersCache.ApplyModifiers(this, SkillAttribute.ManaCost, cost2);
            caster.ReduceCurrentMp(null, manaCost);
            if (caster is Character character)
            {
                character.LastCast = DateTime.UtcNow;
                character.IsInPostCast = true;
            }
        }

    }
}
