using AAEmu.Game.Models.Game.World.Transform;
using AAEmu.Game.Models.Json;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

public class DoodadSpawnReplacementTests
{
    [Test]
    public async Task Contains_UsesHalfOpenWorldBounds()
    {
        var replacement = new JsonDoodadSpawnReplacement
        {
            MinX = 10f,
            MinY = 20f,
            MaxX = 30f,
            MaxY = 40f
        };

        await Assert.That(replacement.Contains(Position(10f, 20f))).IsTrue();
        await Assert.That(replacement.Contains(Position(29.999f, 39.999f))).IsTrue();
        await Assert.That(replacement.Contains(Position(30f, 25f))).IsFalse();
        await Assert.That(replacement.Contains(Position(25f, 40f))).IsFalse();
        await Assert.That(replacement.Contains(Position(9.999f, 25f))).IsFalse();
        await Assert.That(replacement.Contains(Position(25f, 19.999f))).IsFalse();
    }

    private static WorldSpawnPosition Position(float x, float y) => new() { X = x, Y = y };
}
