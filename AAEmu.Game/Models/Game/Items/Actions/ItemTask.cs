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
        /// The 8.0 client uses a fixed 128-byte detail block followed by the
        /// common item timestamps, including ChargeUseSkillTime.
        /// </summary>
        protected static void WriteItemDetails(PacketStream stream, Item item)
        {
            if (item == null)
                throw new System.ArgumentNullException(nameof(item));

            stream.Write(item.TemplateId);
            stream.Write(item.Id);
            stream.Write(item.Grade);
            stream.Write((byte)item.ItemFlags);
            stream.Write(item.Count);

            var details = new PacketStream();
            details.Write((byte)item.DetailType);
            item.WriteDetails(details);
            if (details.Count > 128)
                throw new System.InvalidOperationException($"Item {item.Id} detail payload is {details.Count} bytes; the 8.0 protocol allows 128.");

            stream.Write((short)128);
            stream.Write(details, false);
            stream.Write(new byte[128 - details.Count]);
            stream.Write(item.CreateTime);
            stream.Write(item.LifespanMins);
            stream.Write(item.MadeUnitId);
            stream.Write(item.WorldId);
            stream.Write(item.UnsecureTime);
            stream.Write(item.UnpackTime);
            stream.Write(item.ChargeUseSkillTime);
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
