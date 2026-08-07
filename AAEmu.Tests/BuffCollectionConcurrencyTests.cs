using System;
using System.Collections.Generic;
using System.Reflection;
using System.Threading.Tasks;

using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

using Xunit;

namespace AAEmu.Tests
{
    public class BuffCollectionConcurrencyTests
    {
        [Fact]
        public async Task ReadersTakeAStableSnapshotWhileBuffsAreMutated()
        {
            var buffs = new Buffs(new Unit());
            var flags = BindingFlags.Instance | BindingFlags.NonPublic;
            var gate = typeof(Buffs).GetField("_lock", flags)?.GetValue(buffs);
            var effects = typeof(Buffs).GetField("_effects", flags)?.GetValue(buffs) as List<Buff>;

            Assert.NotNull(gate);
            Assert.NotNull(effects);

            var template = new BuffTemplate { Id = 0xAA8, Stealth = true };
            var sample = new Buff(null, null, null, template, null, DateTime.UtcNow);

            var writer = Task.Run(() =>
            {
                for (var iteration = 0; iteration < 2000; iteration++)
                {
                    lock (gate)
                    {
                        effects.Clear();
                        for (var i = 0; i < 256; i++)
                            effects.Add(sample);
                    }
                }
            });

            var reader = Task.Run(() =>
            {
                for (var iteration = 0; iteration < 20000; iteration++)
                {
                    var count = buffs.GetBuffCountById(template.Id);
                    Assert.InRange(count, 0, 256);
                    _ = buffs.HasStealth();
                    _ = buffs.GetAbsorptionEffects();
                }
            });

            await Task.WhenAll(writer, reader);
        }
    }
}
