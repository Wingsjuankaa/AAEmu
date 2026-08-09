using AAEmu.Commons.Network;

namespace AAEmu.Game.Models.Game.Items.Actions
{
    public abstract class ItemTask : PacketMarshaler
    {
        protected ItemAction _type;
        protected ItemTaskLogType _logType = ItemTaskLogType.UpdateOnly;

        public ItemAction Type => _type;
        public ItemTaskLogType LogType => _logType;

        public override PacketStream Write(PacketStream stream)
        {
            stream.Write((byte)_type); // task action
            stream.Write((byte)_logType); // presentation/audit category

            return stream;
        }

        /// <summary>
        /// Writes the common item payload used by Create, Take and ChangeOwner.
        /// AA8 serializes this value with the same variable-length detail
        /// payload used by the full inventory snapshot. The 128-byte buffer in
        /// the client is in-memory storage, not a fixed-size wire block.
        /// </summary>
        protected static void WriteItemDetails(PacketStream stream, Item item)
        {
            if (item == null)
                throw new System.ArgumentNullException(nameof(item));

            item.Write(stream);
        }
    }

    public enum ItemTaskLogType : byte
    {
        UpdateOnly = 0,
        GainItem = 1,
        RemoveItem = 2,
        MoveItem = 3,
        SwapItem = 4,
        Place = 5
    }

    public enum ItemAction
    {
        Invalid = 0,
        ChangeMoneyAmount = 1,
        ChangeBankMoneyAmount = 2,
        ChangeGamePoint = 3,
        // Introduced before AddStack in the 8.0 protocol. Its wire payload is
        // a UInt32 currency type followed by an Int64 amount. Keeping this
        // placeholder is essential because every subsequent action id moved.
        ChangeTypedPoint = 4,
        AddStack = 5,
        Create = 6,
        Take = 7,
        Remove = 8,
        SwapSlot = 9,
        UpdateDetail = 10,
        SetFlagsBits = 11,
        UpdateFlags = 12,
        RemoveCrafting = 13,
        Seize = 14,
        ChangeGrade = 15,
        ChangeOwner = 16,
        ChangeAaPoint = 17,
        ChangeBankAaPoint = 18,
        ChangeAutoUseAaPoint = 19,
        UpdateChargeUseSkillTime = 20,
    }
}
