using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class MatePersistenceTests
{
    [Test]
    public async Task DisconnectSnapshotCapturesEveryRelogField()
    {
        var updatedAt = DateTime.UnixEpoch.AddDays(123);
        var mate = new Mate
        {
            Hp = 321,
            Mp = 654,
            Level = 37,
            Experience = 7654321,
            Mileage = 88,
            Name = "Snowmane"
        };
        var persisted = new MateDb();

        persisted.Capture(mate, updatedAt);

        await Assert.That(persisted.Hp).IsEqualTo(321);
        await Assert.That(persisted.Mp).IsEqualTo(654);
        await Assert.That(persisted.Level).IsEqualTo((ushort)37);
        await Assert.That(persisted.Xp).IsEqualTo(7654321);
        await Assert.That(persisted.Mileage).IsEqualTo(88);
        await Assert.That(persisted.Name).IsEqualTo("Snowmane");
        await Assert.That(persisted.UpdatedAt).IsEqualTo(updatedAt);
    }
}
