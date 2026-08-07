using System;
using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Models.Game.Items.Services
{
    public sealed class SelectiveItemSnapshot
    {
        public ulong Id { get; set; }
        public SlotType SlotType { get; set; }
        public byte Slot { get; set; }
        public uint TemplateId { get; set; }
        public int Count { get; set; }
    }

    /// <summary>
    /// Builds the authoritative AA8 inventory delta for a selective-item
    /// exchange. Item ids may be immediately reused after consuming the crate;
    /// a reused id with a different identity must be sent as Remove + Create.
    /// </summary>
    public static class SelectiveItemDeltaBuilder
    {
        public static List<ItemTask> Build(
            IReadOnlyDictionary<ulong, SelectiveItemSnapshot> before,
            IReadOnlyDictionary<ulong, Item> after)
        {
            if (before == null)
                throw new ArgumentNullException(nameof(before));
            if (after == null)
                throw new ArgumentNullException(nameof(after));

            var tasks = new List<ItemTask>();
            foreach (var previous in before.Values)
            {
                if (!after.TryGetValue(previous.Id, out var current))
                {
                    tasks.Add(CreateRemove(previous));
                    continue;
                }

                if (previous.TemplateId != current.TemplateId ||
                    previous.SlotType != current.SlotType ||
                    previous.Slot != (byte)current.Slot)
                {
                    tasks.Add(CreateRemove(previous));
                    tasks.Add(new ItemAdd(current));
                    continue;
                }

                var delta = current.Count - previous.Count;
                if (delta != 0)
                    tasks.Add(new ItemCountUpdate(current, delta));
            }

            foreach (var current in after.Values)
                if (!before.ContainsKey(current.Id))
                    tasks.Add(new ItemAdd(current));

            return tasks;
        }

        private static ItemRemove CreateRemove(
            SelectiveItemSnapshot previous)
        {
            return new ItemRemove(
                previous.Id,
                previous.SlotType,
                previous.Slot,
                previous.TemplateId);
        }
    }
}
