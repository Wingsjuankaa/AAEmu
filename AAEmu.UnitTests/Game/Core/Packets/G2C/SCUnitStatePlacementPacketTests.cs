using AAEmu.Commons.Network;
using AAEmu.Game.Core.Packets.G2C.UnitState;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;

namespace AAEmu.UnitTests.Game.Core.Packets.G2C;

public class SCUnitStatePlacementPacketTests
{
    [Test]
    public async Task CharacterSecondaryLevelOverride_IsZeroSoClientIncludesEquipmentStats()
    {
        var character = new Character(new UnitCustomModelParams())
        {
            Level = 55,
            HeirLevel = 30,
            ModelId = 0x01020304
        };
        var stream = new PacketStream();

        UnitStatePlacementSerializer.Write(
            stream,
            new UnitStateWireContext(character, BaseUnitType.Character));

        var body = stream.GetBytes();

        // wpos(11), scale(4), primary level/heirLevel(2), secondary override(2).
        await Assert.That(unchecked((sbyte)body[15])).IsEqualTo((sbyte)55);
        await Assert.That(unchecked((sbyte)body[16])).IsEqualTo(checked((sbyte)character.HeirLevel));
        await Assert.That(unchecked((sbyte)body[17])).IsEqualTo((sbyte)0);
        await Assert.That(unchecked((sbyte)body[18])).IsEqualTo((sbyte)0);

        // AA10 x2game reads four signed slot selectors here and excludes every non-negative slot
        // from its local item/modifier aggregate.  All must remain unset for a normal character.
        for (var index = 19; index < 23; index++)
            await Assert.That(unchecked((sbyte)body[index])).IsEqualTo((sbyte)-1);

        await Assert.That(BitConverter.ToUInt32(body, 23)).IsEqualTo(character.ModelId);
    }
}
