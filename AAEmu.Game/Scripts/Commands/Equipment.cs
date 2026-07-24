using System;

using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.Game.Scripts.Commands
{
    public class Equipment : ICommand
    {
        public void OnLoad()
        {
            CommandManager.Instance.Register("equipment", this);
        }

        public string GetCommandLineHelp()
        {
            return "audit [self|target] | resync [self|target]";
        }

        public string GetCommandHelpText()
        {
            return "Audits the canonical 32-slot equipment state or resends it to the client.";
        }

        public void Execute(Character character, string[] args)
        {
            if (args.Length == 0 || !TryTarget(character, args.Length > 1 ? args[1] : "self", out var target))
            {
                character.SendMessage("[Equipment] /equipment audit [self|target] | resync [self|target]");
                return;
            }

            switch (args[0].ToLowerInvariant())
            {
                case "audit":
                    Audit(character, target);
                    break;
                case "resync":
                    EquipmentSyncService.Instance.Resync(target);
                    character.SendMessage("[Equipment] Sent authoritative 32-slot state for {0}.", target.Name);
                    break;
                default:
                    character.SendMessage("[Equipment] /equipment audit [self|target] | resync [self|target]");
                    break;
            }
        }

        private static void Audit(Character issuer, Character target)
        {
            var items = target.Inventory.Equipment.GetSlottedItemsList();
            var validFlags = EquipmentPacketMasks.BuildValidFlags(items);
            var itemFlags = EquipmentPacketMasks.BuildItemFlags(items);
            var main = target.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Mainhand);
            var off = target.Inventory.Equipment.GetItemBySlot((int)EquipmentItemSlot.Offhand);
            var invalidHands = EquipmentRuleService.Instance.IsTwoHanded(main) && off != null;

            issuer.SendMessage(
                "[Equipment] {0}: items={1}, validFlags=0x{2:X8}, flags=0x{3:X8}, invalidHands={4}",
                target.Name, target.Inventory.Equipment.Items.Count, validFlags, itemFlags, invalidHands);
            for (byte slot = 0; slot < EquipmentPacketMasks.PhysicalSlotCount; slot++)
            {
                var item = target.Inventory.Equipment.GetItemBySlot(slot);
                if (item != null)
                    issuer.SendMessage(
                        "[Equipment] slot={0}({1}) instance={2} template={3} grade={4} durability={5}/{6}",
                        slot, Enum.IsDefined(typeof(EquipmentItemSlot), slot) ? ((EquipmentItemSlot)slot).ToString() : "reserved",
                        item.Id, item.TemplateId, item.Grade,
                        item is EquipItem equipment ? equipment.Durability : (byte)0,
                        item is EquipItem equipmentMax ? equipmentMax.MaxDurability : (byte)0);
            }
        }

        private static bool TryTarget(Character issuer, string selector, out Character target)
        {
            target = issuer;
            if (selector.Equals("self", StringComparison.OrdinalIgnoreCase))
                return true;
            if (selector.Equals("target", StringComparison.OrdinalIgnoreCase) &&
                issuer.CurrentTarget is Character selected)
            {
                target = selected;
                return true;
            }

            issuer.SendMessage("[Equipment] Select a character target or use self.");
            return false;
        }
    }
}
