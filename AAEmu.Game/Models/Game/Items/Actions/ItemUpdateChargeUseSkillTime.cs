using System;
using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public class ItemUpdateChargeUseSkillTime : ItemTask
    {
        private readonly ulong _itemId;
        private readonly SlotType _slotType;
        private readonly byte _slot;
        private readonly DateTime _chargeUseSkillTime;

        public ItemUpdateChargeUseSkillTime(Item item)
            : this(item?.Id ?? throw new ArgumentNullException(nameof(item)), item.SlotType,
                (byte)item.Slot, item.ChargeUseSkillTime)
        {
        }

        public ItemUpdateChargeUseSkillTime(ulong itemId, SlotType slotType, byte slot, DateTime chargeUseSkillTime)
        {
            _type = ItemAction.UpdateChargeUseSkillTime;
            _logType = ItemTaskLogType.UpdateOnly;
            _itemId = itemId;
            _slotType = slotType;
            _slot = slot;
            _chargeUseSkillTime = chargeUseSkillTime;
        }

        public override PacketStream Write(PacketStream stream)
        {
            base.Write(stream);
            stream.Write((byte)_slotType);
            stream.Write(_slot);
            stream.Write(_itemId);
            stream.Write(_chargeUseSkillTime);
            return stream;
        }
    }
}
