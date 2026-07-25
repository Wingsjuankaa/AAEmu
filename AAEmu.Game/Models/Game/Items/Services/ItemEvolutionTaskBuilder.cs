using System;
using System.Collections.Generic;

using AAEmu.Game.Models.Game.Items.Actions;

namespace AAEmu.Game.Models.Game.Items.Services
{
    /// <summary>
    /// Builds the native AA8 ItemTask actions required to synchronize an
    /// evolved item. Grade is stored outside the 128-byte detail block, so a
    /// grade transition requires ChangeGrade before UpdateDetail.
    /// </summary>
    public static class ItemEvolutionTaskBuilder
    {
        public static IReadOnlyList<ItemTask> CreateGradeAndDetailUpdate(
            Item item,
            byte beforeGrade,
            byte afterGrade)
        {
            if (item == null)
                throw new ArgumentNullException(nameof(item));
            if (item.Grade != afterGrade)
                throw new ArgumentException(
                    "The item grade must match the post-evolution grade.",
                    nameof(afterGrade));

            var tasks = new List<ItemTask>(2);
            if (beforeGrade != afterGrade)
                tasks.Add(new ItemGradeChange(item, afterGrade));
            tasks.Add(new ItemUpdate(item));
            return tasks;
        }
    }
}
