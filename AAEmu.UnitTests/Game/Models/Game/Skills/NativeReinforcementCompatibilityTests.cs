using System.Reflection;
using AAEmu.Commons.Network;
using AAEmu.Game.Models.Game.Char;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class NativeReinforcementCompatibilityTests
{
    [Test]
    public async Task CommunitySurfaceReadsTheNativeSnapshotAndNeverUsesItsCompetingSchema()
    {
        var owner = new Character(null);
        owner.EquipSlotReinforce = new CharacterEquipSlotReinforce(owner);
        var snapshot = new EquipSlotReinforceState(
            new Dictionary<byte, EquipSlotReinforceProgress> { [2] = new(5, 321) });
        typeof(CharacterEquipSlotReinforce).GetField("_state", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(owner.EquipSlotReinforce, snapshot);
        var compatibility = new CharacterEquipSlotReinforces(owner);

        // A second load/save must not access the incompatible community column layout.
        compatibility.Load(null);
        compatibility.Save(null, null);
        await Assert.That(compatibility.StateOf(2).Level).IsEqualTo((sbyte)5);
        await Assert.That(compatibility.StateOf(2).Exp).IsEqualTo(321);
        await Assert.That(compatibility.States.Count).IsEqualTo(1);

        var actual = new PacketStream();
        var expected = new PacketStream();
        compatibility.WriteInfos(actual);
        snapshot.Write(expected);
        await Assert.That(Convert.ToHexString(actual.GetBytes())).IsEqualTo(Convert.ToHexString(expected.GetBytes()));
        await Assert.That(compatibility.SetProgress(2, 9, 0, out _)).IsFalse();
        await Assert.That(owner.EquipSlotReinforce.Snapshot).IsSameReferenceAs(snapshot);
    }
}
