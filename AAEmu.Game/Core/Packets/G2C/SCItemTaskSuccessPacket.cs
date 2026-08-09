using System.Collections.Generic;
using System;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCItemTaskSuccessPacket : GamePacket
    {
        private readonly byte _unitOwnerType;
        private readonly ItemTaskType _action;
        private readonly List<ItemTask> _tasks;
        private readonly List<ulong> _forceRemove;
        private readonly uint _type;
        private readonly uint _lockItemSlotKey;
        private readonly uint _flags;

        public SCItemTaskSuccessPacket(ItemTaskType action, List<ItemTask> tasks, List<ulong> forceRemove,
            uint type = 0, uint lockItemSlotKey = 0, byte unitOwnerType = 0, uint flags = 0) : base(SCOffsets.SCItemTaskSuccessPacket, 5)
        {
            _unitOwnerType = unitOwnerType;
            _action = action;
            _tasks = tasks != null
                ? new List<ItemTask>(tasks)
                : throw new ArgumentNullException(nameof(tasks));
            _forceRemove = forceRemove != null
                ? new List<ulong>(forceRemove)
                : new List<ulong>();
            _type = type;
            _lockItemSlotKey = lockItemSlotKey;
            _flags = flags;
        }

        public SCItemTaskSuccessPacket(ItemTaskType action, ItemTask task, List<ulong> forceRemove,
            uint type = 0, uint lockItemSlotKey = 0, byte unitOwnerType = 0, uint flags = 0) : base(SCOffsets.SCItemTaskSuccessPacket, 5)
        {
            _unitOwnerType = unitOwnerType;
            _action = action;
            _tasks = new List<ItemTask>
            {
                task ?? throw new ArgumentNullException(nameof(task))
            };
            _forceRemove = forceRemove != null
                ? new List<ulong>(forceRemove)
                : new List<ulong>();
            _type = type;
            _lockItemSlotKey = lockItemSlotKey;
            _flags = flags;
        }

        public override PacketStream Write(PacketStream stream)
        {
            const int maxBatchSize = 30;
            if (_tasks.Count > maxBatchSize)
                throw new InvalidOperationException($"SCItemTaskSuccessPacket contains {_tasks.Count} tasks; the 8.0 client limit is {maxBatchSize}.");
            if (_forceRemove.Count > maxBatchSize)
                throw new InvalidOperationException($"SCItemTaskSuccessPacket contains {_forceRemove.Count} forced removals; the 8.0 client limit is {maxBatchSize}.");

            stream.Write(_unitOwnerType);
            stream.Write((byte)_action);

            stream.Write((byte)_tasks.Count);
            foreach (var task in _tasks)
            {
                if (task == null)
                    throw new InvalidOperationException("SCItemTaskSuccessPacket cannot serialize a null task.");
                stream.Write(task);
            }

            stream.Write((byte)_forceRemove.Count);
            foreach (var remove in _forceRemove)
                stream.Write(remove);

            stream.Write(_type);
            stream.Write(_lockItemSlotKey);
            stream.Write(_flags);
            return stream;
        }

        public override string Verbose()
        {
            return $" - ownerType: {_unitOwnerType}, action: {_action}, tasks: {_tasks.Count}, forceRemove: {_forceRemove.Count}, type: {_type}, lock: {_lockItemSlotKey}, flags: 0x{_flags:X8}";
        }
    }
}
