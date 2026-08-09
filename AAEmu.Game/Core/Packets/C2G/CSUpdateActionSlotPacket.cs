using AAEmu.Commons.Network;
using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.Game.Core.Packets.C2G
{
    public class CSUpdateActionSlotPacket : GamePacket
    {
        public CSUpdateActionSlotPacket() : base(CSOffsets.CSUpdateActionSlotPacket, 5)
        {
        }

        public override void Read(PacketStream stream)
        {
            // Confirmed in x2game.dll FUN_399a7970 + FUN_3999be30:
            // byte slot, byte type, then uint32 for 1/2/5/6 or uint64 for 4.
            var character = Connection.ActiveChar;
            if (!ActionSlotWireCodec.TryReadUpdate(
                    stream,
                    out var slot,
                    out var type,
                    out var actionId,
                    out var wireError))
            {
                Reject(
                    character,
                    slot,
                    type,
                    actionId,
                    wireError);
                return;
            }

            if (character == null)
                return;
            if (slot >= Character.MaxActionSlots)
            {
                Reject(character, slot, type, actionId, "slot is outside the AA8 217-slot range");
                return;
            }

            var valid = true;
            switch (type)
            {
                case ActionSlotType.ItemType:
                    valid = ItemManager.Instance.GetTemplate((uint)actionId) != null;
                    break;
                case ActionSlotType.Spell:
                case ActionSlotType.RidePetSpell:
                case ActionSlotType.BattlePetSpell:
                    valid = SkillManager.Instance.GetSkillTemplate((uint)actionId) != null;
                    break;
                case ActionSlotType.ItemId:
                    var item = ItemManager.Instance.GetItemByItemId(actionId);
                    valid = item != null && item.OwnerId == character.Id;
                    break;
            }

            if (!valid)
            {
                Reject(
                    character,
                    slot,
                    type,
                    actionId,
                    "action does not resolve in the authoritative catalogue");
                return;
            }

            character.SetAction(slot, type, actionId);
        }

        private void Reject(
            Character character,
            byte slot,
            ActionSlotType type,
            ulong actionId,
            string reason)
        {
            _log.Warn(
                "Rejected AA8 action-slot update for {0}: slot={1}, type={2}, action={3}, reason={4}",
                character?.Name ?? "<none>",
                slot,
                type,
                actionId,
                reason);
            if (character != null)
                Connection.SendPacket(new SCActionSlotsPacket(character.Slots));
        }
    }
}
