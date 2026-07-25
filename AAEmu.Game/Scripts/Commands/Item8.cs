using System;
using System.Linq;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;
using AAEmu.Game.Models.Game.Items.Templates;
using AAEmu.Game.Utils.DB;

namespace AAEmu.Game.Scripts.Commands
{
    public class Item8 : ICommand
    {
        public void OnLoad()
        {
            CommandManager.Instance.Register("item8", this);
        }

        public string GetCommandLineHelp()
        {
            return "search <text> [all|weapon|armor|accessory|consumable] [level] | info <itemId> | coverage <itemId> | socket <itemId> | evolution <itemId> [grade] | synthesis <itemId> | awakening <itemId> | evolutionstate <instanceId> | evolutioncoverage <itemId> | regrade <itemId> <grade> | appearance <itemId> | salvage <itemId> | quarantine list [owner]";
        }

        public string GetCommandHelpText()
        {
            return "Searches and inspects the authoritative AA8 item catalogue and its backend coverage.";
        }

        public void Execute(Character character, string[] args)
        {
            if (args.Length < 2)
            {
                SendUsage(character);
                return;
            }

            switch (args[0].ToLowerInvariant())
            {
                case "quarantine":
                    Quarantine(character, args);
                    break;
                case "search":
                    Search(character, args);
                    break;
                case "info":
                case "coverage":
                case "socket":
                case "evolution":
                case "synthesis":
                case "awakening":
                case "evolutionstate":
                case "evolutioncoverage":
                case "regrade":
                case "appearance":
                case "salvage":
                    if (!uint.TryParse(args[1], out var itemId))
                    {
                        character.SendMessage("[Item8] itemId must be an unsigned AA8 item id.");
                        return;
                    }
                    if (args[0].Equals("socket", StringComparison.OrdinalIgnoreCase))
                        ShowSocket(character, itemId);
                    else if (args[0].Equals("evolution", StringComparison.OrdinalIgnoreCase))
                        ShowEvolution(character, itemId, args);
                    else if (args[0].Equals("synthesis", StringComparison.OrdinalIgnoreCase))
                        ShowSynthesis(character, itemId);
                    else if (args[0].Equals("awakening", StringComparison.OrdinalIgnoreCase))
                        ShowAwakening(character, itemId);
                    else if (args[0].Equals("evolutionstate", StringComparison.OrdinalIgnoreCase))
                        ShowEvolutionState(character, itemId);
                    else if (args[0].Equals("evolutioncoverage", StringComparison.OrdinalIgnoreCase))
                        ShowEvolutionCoverage(character, itemId);
                    else if (args[0].Equals("regrade", StringComparison.OrdinalIgnoreCase))
                        ShowRegrade(character, itemId, args);
                    else if (args[0].Equals("appearance", StringComparison.OrdinalIgnoreCase))
                        ShowAppearance(character, itemId);
                    else if (args[0].Equals("salvage", StringComparison.OrdinalIgnoreCase))
                        ShowSalvaging(character, itemId);
                    else
                        Show(character, itemId, args[0].Equals("coverage", StringComparison.OrdinalIgnoreCase));
                    break;
                default:
                    SendUsage(character);
                    break;
            }
        }

        private static void ShowSynthesis(Character character, uint itemId)
        {
            var item = ResolveEquipment(character, itemId);
            var templateId = item?.TemplateId ?? itemId;
            var grade = item?.Grade ?? 0;
            var profile = ItemEvolutionRuleService.Instance.GetProfile(
                templateId,
                grade);
            character.SendMessage(
                "[Item8] synthesis item={0} template={1} grade={2} category={3} valid={4}",
                itemId, templateId, grade, profile.CategoryId,
                profile.HasSynthesisDefinition);
            if (profile.Property == null)
                return;
            character.SendMessage(
                "[Item8] sectionXp={0}/{1} goldMul={2} bonusChance={3} bonus={4}..{5} maxAttrs={6}",
                item?.EvolutionExperience ?? 0,
                profile.Property.GradeExp,
                profile.Property.GoldMultiplier,
                profile.Property.BonusExpChance,
                profile.Property.BonusExpMin,
                profile.Property.BonusExpMax,
                profile.Property.MaxUnitModifierNum);
            character.SendMessage(
                "[Item8] validMaterials={0}; provenance=client_compact_8+game11_native+x2game_confirmed",
                profile.ValidMaterialItemIds.Count);
        }

        private static void ShowAwakening(Character character, uint itemId)
        {
            var item = ResolveEquipment(character, itemId);
            var templateId = item?.TemplateId ?? itemId;
            var grade = item?.Grade ?? 0;
            var profile = ItemEvolutionRuleService.Instance.GetProfile(
                templateId,
                grade);
            character.SendMessage(
                "[Item8] awakening item={0} template={1} grade={2} mappings={3}",
                itemId, templateId, grade, profile.AwakeningMappings.Count);
            foreach (var mapping in profile.AwakeningMappings.Take(12))
            {
                var group = ItemEvolutionRuleService.Instance.GetMappingGroup(
                    mapping.MappingGroupId);
                character.SendMessage(
                    "[Item8] map={0} group={1} target={2}@{3} chanceRaw={4} failBonus={5} inheritXp={6} selectable={7}",
                    mapping.Id, mapping.MappingGroupId, mapping.TargetItemId,
                    mapping.TargetGradeId, group?.Success ?? 0,
                    group?.FailBonus ?? 0, group?.EvolvingExpInherit ?? false,
                    group?.Selectable ?? false);
                foreach (var reactive in
                         ItemEvolutionRuleService.Instance
                             .GetAwakeningReactives(mapping.MappingGroupId))
                    character.SendMessage(
                        "[Item8] reactive={0} skill={1} count={2} labor={3} nativeV2={4} nativeV4={5}",
                        reactive.ItemId, reactive.SkillId,
                        reactive.ConsumeCount, reactive.LaborCost,
                        reactive.NativeValue2, reactive.NativeValue4);
            }
            character.SendMessage(
                "[Item8] reactive relation is native AA8; mutation remains blocked until chance/failure serialization is confirmed.");
        }

        private static void ShowEvolutionState(Character character, uint instanceId)
        {
            var item = character.Inventory.GetItemById(instanceId) as EquipItem;
            if (item == null)
            {
                character.SendMessage(
                    "[Item8] Equipment instance {0} is not in your inventory.",
                    instanceId);
                return;
            }
            var state = ItemEvolutionStateService.Instance.Read(item);
            character.SendMessage(
                "[Item8] evolutionstate instance={0} template={1} grade={2} sectionXp={3} chance={4} failBonus={5}",
                instanceId, state.ItemTemplateId, state.GradeId,
                state.SectionExperience, state.EvolutionChance,
                state.MappingFailBonus);
            character.SendMessage(
                "[Item8] randomModifierIds={0}",
                string.Join(",", state.RandomModifierIds));
            foreach (var modifier in ItemRandomAttributeService.Instance
                         .GetCurrentValues(item))
            {
                character.SendMessage(
                    "[Item8] attr row={0} group={1} attribute={2} type={3} value={4}",
                    modifier.ModifierId, modifier.GroupId,
                    modifier.UnitAttributeId, modifier.UnitModifierTypeId,
                    modifier.Value);
            }
        }

        private static void ShowEvolutionCoverage(Character character, uint itemId)
        {
            var profile = ItemEvolutionRuleService.Instance.GetProfile(itemId, 0);
            character.SendMessage(
                "[Item8] evolutioncoverage item={0} category={1} properties={2} materials={3} attrs={4} awakenings={5}",
                itemId, profile.Category != null,
                profile.Property != null, profile.ValidMaterialItemIds.Count,
                profile.ModifierGroupSets.Count,
                profile.AwakeningMappings.Count);
            character.SendMessage(
                "[Item8] runtime provenance excludes historical_3_0; unknown awakening reactives keep mutation isolated.");
        }

        private static EquipItem ResolveEquipment(
            Character character,
            uint itemOrTemplateId)
        {
            return character.Inventory.GetItemById(itemOrTemplateId) as EquipItem ??
                   character.Inventory.Bag.Items
                       .OfType<EquipItem>()
                       .FirstOrDefault(item => item.TemplateId == itemOrTemplateId);
        }

        private static void ShowSalvaging(Character character, uint itemId)
        {
            var service = ItemSalvagingCatalogueService.Instance;
            if (!service.NativeCatalogueAvailable)
            {
                character.SendMessage("[Item8] Native AA8 Phase B6 catalogue is not active.");
                return;
            }

            var coverage = service.GetCoverage(itemId);
            character.SendMessage(
                "[Item8] salvage item={0} reagents={1} products={2} smelting={3}",
                itemId, coverage.ReagentDefinitions, coverage.ProductDefinitions,
                coverage.SmeltingDefinitions);
            character.SendMessage(
                "[Item8] B6 is catalogue-only: conversion/smelting mutation remains blocked until probabilities and AA8 protocol are confirmed.");
        }

        private static void ShowAppearance(Character character, uint itemId)
        {
            var template = ItemManager.Instance.GetTemplate(itemId) as EquipItemTemplate;
            if (template == null)
            {
                character.SendMessage(
                    "[Item8] Item {0} is not AA8 equipment in the active catalogue.",
                    itemId);
                return;
            }

            var conversion = template.ItemLookConvert;
            if (conversion == null)
            {
                character.SendMessage(
                    "[Item8] Item {0} has no native AA8 appearance conversion.",
                    itemId);
                return;
            }

            character.SendMessage(
                "[Item8] appearance item={0} convert={1} gold={2} required={3}x{4} revert={5}x{6}",
                itemId, conversion.Id, conversion.Gold,
                conversion.RequiredItemId, conversion.RequiredItemCount,
                conversion.RevertItemId, conversion.RevertItemCount);
            character.SendMessage(
                "[Item8] B5 is catalogue-only: appearance mutation remains blocked until its AA8 protocol and rollback are confirmed.");
        }

        private static void ShowRegrade(Character character, uint itemId, string[] args)
        {
            var service = ItemRegradeRuleService.Instance;
            if (!service.NativeCatalogueAvailable)
            {
                character.SendMessage("[Item8] Native AA8 Phase B4 catalogue is not active.");
                return;
            }
            if (args.Length < 3 || !int.TryParse(args[2], out var grade))
            {
                character.SendMessage("[Item8] /item8 regrade <itemId> <grade>");
                return;
            }

            var profile = service.GetProfile(itemId, grade);
            if (!profile.HasNativeRatio)
            {
                character.SendMessage(
                    "[Item8] No native AA8 regrade ratio for item={0}, grade={1}.",
                    itemId, grade);
                return;
            }

            character.SendMessage(
                "[Item8] regrade item={0} grade={1} group={2} kind={3} impl={4}",
                itemId, grade, profile.GroupId, profile.Group.KindId,
                profile.Group.ItemImplId);
            character.SendMessage(
                "[Item8] success={0} great={1} break={2} downgrade={3} disable={4} cost={5} currency={6} down={7}..{8}",
                profile.Ratio.Success, profile.Ratio.GreatSuccess,
                profile.Ratio.Break, profile.Ratio.Downgrade,
                profile.Ratio.Disable, profile.Ratio.Cost,
                profile.Ratio.CurrencyId, profile.Ratio.DowngradeMin,
                profile.Ratio.DowngradeMax);
            character.SendMessage(
                "[Item8] B4 is catalogue-only: regrade mutation remains blocked until the AA8 transaction and break rewards are confirmed.");
        }

        private static void ShowEvolution(Character character, uint itemId, string[] args)
        {
            var service = ItemEvolutionRuleService.Instance;
            if (!service.NativeCatalogueAvailable)
            {
                character.SendMessage("[Item8] Native AA8 Phase B3 catalogue is not active.");
                return;
            }

            var grade = 0;
            if (args.Length > 2 && !int.TryParse(args[2], out grade))
            {
                character.SendMessage("[Item8] grade must be a numeric AA8 grade id.");
                return;
            }

            var profile = service.GetProfile(itemId, grade);
            character.SendMessage(
                "[Item8] evolution item={0} grade={1} category={2} synthesis={3} material={4} awakening={5}",
                itemId, grade, profile.CategoryId, profile.HasSynthesisDefinition,
                profile.IsSynthesisMaterial, profile.HasAwakeningDefinition);

            if (profile.Category != null)
            {
                character.SendMessage(
                    "[Item8] currency={0} group={1} materialGradeLimit={2} maxEvolvingGrade={3} rerollSet={4}",
                    profile.Category.CurrencyId, profile.Category.CategoryGroupId,
                    profile.Category.MaterialGradeLimit,
                    profile.Category.MaxEvolvingGrade,
                    profile.Category.ReRollItemSetId);
            }

            if (profile.Property != null)
            {
                character.SendMessage(
                    "[Item8] gradeExp={0} gainExp={1} bonusChance={2} bonusExp={3}..{4} goldMul={5} maxElement={6} maxModifiers={7}",
                    profile.Property.GradeExp, profile.Property.GainExp,
                    profile.Property.BonusExpChance, profile.Property.BonusExpMin,
                    profile.Property.BonusExpMax, profile.Property.GoldMultiplier,
                    profile.Property.MaxElementLevel,
                    profile.Property.MaxUnitModifierNum);
            }
            else if (profile.Category != null)
            {
                character.SendMessage(
                    "[Item8] No native synthesis property exists for category={0}, grade={1}.",
                    profile.CategoryId, grade);
            }

            foreach (var mapping in profile.AwakeningMappings.Take(12))
            {
                var group = service.GetMappingGroup(mapping.MappingGroupId);
                var targetCoverage = ItemDefinitionCoverageService.Instance.Get(
                    mapping.TargetItemId);
                character.SendMessage(
                    "[Item8] awaken map={0} group={1} target={2}@grade{3} success={4} failBonus={5} selectable={6} targetCoverage={7}",
                    mapping.Id, mapping.MappingGroupId, mapping.TargetItemId,
                    mapping.TargetGradeId, group?.Success ?? 0,
                    group?.FailBonus ?? 0, group?.Selectable ?? false,
                    targetCoverage.State);
            }

            character.SendMessage(
                "[Item8] B3 is catalogue-only: synthesis/awakening mutation remains blocked until AA8 protocol and costs are confirmed.");
        }

        private static void ShowSocket(Character character, uint itemId)
        {
            var service = ItemSocketRuleService.Instance;
            var definition = service.GetDefinition(itemId);
            if (!service.NativeCatalogueAvailable)
            {
                character.SendMessage("[Item8] Native AA8 Phase B1 catalogue is not active.");
                return;
            }

            if (definition == null)
            {
                character.SendMessage("[Item8] Item {0} has no AA8 socket/lunagem definition.", itemId);
                return;
            }

            character.SendMessage(
                "[Item8] socket item={0} nativeId={1} kind={2} slotGroup={3} exactTarget={4} grade={5} level={6}",
                definition.ItemId,
                definition.Id,
                definition.Kind,
                definition.EquipSlotGroupId,
                definition.EquipItemId,
                definition.ItemGradeId,
                definition.EquipLevel);
            character.SendMessage(
                "[Item8] chanceSet={0} guaranteed={1} extractable={2} eiset={3} tag={4} ignoreTag={5} visualFx={6}",
                definition.ItemSocketChanceId,
                definition.Guaranteed,
                definition.Extractable,
                definition.EisetId,
                definition.EquipItemTagId,
                definition.IgnoreEquipItemTag,
                definition.GemVisualEffectId);
            if (definition.Guaranteed)
                character.SendMessage(
                    "[Item8] guarantee evidence: {0}",
                    definition.GuaranteeEvidence);
        }

        private static void Quarantine(Character character, string[] args)
        {
            if (args.Length < 2 || !args[1].Equals("list", StringComparison.OrdinalIgnoreCase))
            {
                SendUsage(character);
                return;
            }

            using (var connection = MySQL.CreateConnection())
            {
                if (connection == null)
                {
                    character.SendMessage("[Item8] Unable to connect to the game database.");
                    return;
                }

                using (var exists = connection.CreateCommand())
                {
                    exists.CommandText =
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=DATABASE() AND table_name='quarantined_items'";
                    if (Convert.ToInt32(exists.ExecuteScalar()) == 0)
                    {
                        character.SendMessage("[Item8] quarantined_items has not been installed yet.");
                        return;
                    }
                }

                using (var command = connection.CreateCommand())
                {
                    command.CommandText =
                        "SELECT q.id,q.owner,q.template_id,q.slot_type,q.slot,q.quarantine_reason,q.quarantined_at " +
                        "FROM quarantined_items q LEFT JOIN characters c ON c.id=q.owner " +
                        "WHERE q.restored_at IS NULL ";
                    if (args.Length > 2)
                    {
                        command.CommandText += "AND (CAST(q.owner AS CHAR)=@owner OR c.name=@owner) ";
                        command.Parameters.AddWithValue("@owner", args[2]);
                    }
                    command.CommandText += "ORDER BY q.quarantined_at DESC LIMIT 50";

                    using (var reader = command.ExecuteReader())
                    {
                        var count = 0;
                        while (reader.Read())
                        {
                            count++;
                            character.SendMessage(
                                "[Item8] quarantine instance={0} owner={1} template={2} slot={3}:{4} reason={5} at={6:u}",
                                reader.GetUInt64(reader.GetOrdinal("id")), reader.GetUInt32(reader.GetOrdinal("owner")),
                                reader.GetUInt32(reader.GetOrdinal("template_id")), reader.GetString(reader.GetOrdinal("slot_type")),
                                reader.GetInt32(reader.GetOrdinal("slot")), reader.GetString(reader.GetOrdinal("quarantine_reason")),
                                reader.GetDateTime(reader.GetOrdinal("quarantined_at")));
                        }
                        character.SendMessage("[Item8] {0} quarantined item(s) shown.", count);
                    }
                }
            }
        }

        private static void Search(Character character, string[] args)
        {
            var text = args[1];
            var filter = args.Length > 2 ? args[2].ToLowerInvariant() : "all";
            int? level = null;
            if (args.Length > 3 && int.TryParse(args[3], out var requestedLevel))
                level = requestedLevel;

            var matches = ItemManager.Instance.GetTemplates()
                .Where(template =>
                    ItemDefinitionCoverageService.Instance.Get(template.Id).State !=
                    ItemDefinitionCoverageState.Unknown)
                .Where(template =>
                    (template.Name ?? string.Empty).IndexOf(text, StringComparison.OrdinalIgnoreCase) >= 0)
                .Where(template => !level.HasValue || template.LevelRequirement == level.Value)
                .Where(template => MatchesType(template, filter))
                .OrderBy(template => template.LevelRequirement)
                .ThenBy(template => template.Id)
                .Take(25)
                .ToList();

            character.SendMessage("[Item8] {0} result(s), showing up to 25.", matches.Count);
            foreach (var template in matches)
            {
                var coverage = ItemDefinitionCoverageService.Instance.Get(template.Id);
                character.SendMessage(
                    "[Item8] {0} | {1} | type={2} | level={3} | coverage={4}",
                    template.Id, template.Name, coverage.ConcreteType,
                    template.LevelRequirement, coverage.State);
            }
        }

        private static bool MatchesType(ItemTemplate template, string filter)
        {
            switch (filter)
            {
                case "all":
                    return true;
                case "weapon":
                    return template is WeaponTemplate;
                case "armor":
                    return template is ArmorTemplate;
                case "accessory":
                    return template is AccessoryTemplate;
                case "consumable":
                    return !(template is EquipItemTemplate);
                default:
                    return false;
            }
        }

        private static void Show(Character character, uint itemId, bool coverageOnly)
        {
            var coverage = ItemDefinitionCoverageService.Instance.Get(itemId);
            if (!coverageOnly)
            {
                if (ItemDefinitionCoverageService.Instance.NativeCatalogueAvailable &&
                    coverage.State == ItemDefinitionCoverageState.Unknown)
                {
                    character.SendMessage(
                        "[Item8] Item {0} is not part of the native AA8 catalogue.", itemId);
                    return;
                }

                var template = ItemManager.Instance.GetTemplate(itemId);
                if (template == null)
                {
                    character.SendMessage("[Item8] Item {0} is not present in the active catalogue.", itemId);
                    return;
                }

                character.SendMessage(
                    "[Item8] {0} | {1} | class={2} | level={3} | fixedGrade={4} | gradable={5}",
                    template.Id, template.Name, template.ClassType.Name,
                    template.LevelRequirement, template.FixedGrade, template.Gradable);

                if (template is WeaponTemplate weapon)
                    character.SendMessage("[Item8] holdable={0}, slotType={1}, repairable={2}, durabilityMul={3}",
                        weapon.HoldableTemplate.Id, weapon.HoldableTemplate.SlotTypeId,
                        weapon.Repairable, weapon.DurabilityMultiplier);
                else if (template is ArmorTemplate armor)
                    character.SendMessage("[Item8] armorType={0}, slotType={1}, repairable={2}, durabilityMul={3}",
                        armor.KindTemplate.TypeId, armor.SlotTemplate.SlotTypeId,
                        armor.Repairable, armor.DurabilityMultiplier);
                else if (template is AccessoryTemplate accessory)
                    character.SendMessage("[Item8] accessoryType={0}, slotType={1}, repairable={2}, durabilityMul={3}",
                        accessory.KindTemplate.TypeId, accessory.SlotTemplate.SlotTypeId,
                        accessory.Repairable, accessory.DurabilityMultiplier);
            }

            character.SendMessage(
                "[Item8] coverage={0}, concreteType={1}, missing={2}, provenance={3}",
                coverage.State, coverage.ConcreteType,
                string.IsNullOrEmpty(coverage.MissingDependencies) ? "none" : coverage.MissingDependencies,
                string.IsNullOrEmpty(coverage.Provenance) ? "unknown" : coverage.Provenance);
        }

        private static void SendUsage(Character character)
        {
            character.SendMessage(
                "[Item8] /item8 search <text> [all|weapon|armor|accessory|consumable] [level] | info <itemId> | coverage <itemId> | socket <itemId> | evolution <itemId> [grade] | synthesis <itemId> | awakening <itemId> | evolutionstate <instanceId> | evolutioncoverage <itemId> | regrade <itemId> <grade> | appearance <itemId> | salvage <itemId> | quarantine list [owner]");
        }
    }
}
