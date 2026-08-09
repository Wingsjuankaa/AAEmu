using System.Collections.Generic;
using System;
using AAEmu.Commons.Network;
using AAEmu.Game.Core.Network.Game;
using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Core.Packets.G2C
{
    public class SCItemTaskNotifyPacket : GamePacket
    {
        private readonly ItemTaskType _action;
        private readonly List<ItemTask> _tasks;
        private readonly List<ulong> _forceRemove;
        private readonly uint _type;
        private readonly uint _lockItemSlotKey;

        public SCItemTaskNotifyPacket(ItemTaskType action, List<ItemTask> tasks, List<ulong> forceRemove,
            uint type = 0, uint lockItemSlotKey = 0) : base(SCOffsets.SCItemTaskNotifyPacket, 5)
        {
            _action = action;
            _tasks = tasks != null
                ? new List<ItemTask>(tasks)
                : throw new ArgumentNullException(nameof(tasks));
            _forceRemove = forceRemove != null
                ? new List<ulong>(forceRemove)
                : new List<ulong>();
            _type = type;
            _lockItemSlotKey = lockItemSlotKey;
        }

        public override PacketStream Write(PacketStream stream)
        {
            const int maxBatchSize = 30;
            if (_tasks.Count > maxBatchSize)
                throw new InvalidOperationException($"SCItemTaskNotifyPacket contains {_tasks.Count} tasks; the 8.0 client limit is {maxBatchSize}.");
            if (_forceRemove.Count > maxBatchSize)
                throw new InvalidOperationException($"SCItemTaskNotifyPacket contains {_forceRemove.Count} forced removals; the 8.0 client limit is {maxBatchSize}.");

            stream.Write((byte)_action);

            stream.Write((byte)_tasks.Count);
            foreach (var task in _tasks)
            {
                if (task == null)
                    throw new InvalidOperationException("SCItemTaskNotifyPacket cannot serialize a null task.");
                stream.Write(task);
            }

            stream.Write((byte)_forceRemove.Count);
            foreach (var remove in _forceRemove)
                stream.Write(remove);

            stream.Write(_type);
            stream.Write(_lockItemSlotKey);

            return stream;
        }
    }
}
