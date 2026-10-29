using AAEmu.Commons.Network;
using AAEmu.Commons.Network.Core;
using AAEmu.Game.Core.Network.Connections;
using AAEmu.Game.Core.Packets.G2C;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.StaticValues;
using AAEmu.UnitTests.Utils;

namespace AAEmu.UnitTests.Game.Models.Game.Char;

public class GamePointNotificationTests
{
    [Test]
    [Arguments(GamePointKind.Honor, 200, 0, 200)]
    [Arguments(GamePointKind.Honor, -1200, 0, -1000)]
    [Arguments(GamePointKind.Vocation, 25, 1, 25)]
    [Arguments(GamePointKind.Leadership, 50, 11, 50)]
    [Arguments(GamePointKind.Vocation, -900, 1, -500)]
    [Arguments(GamePointKind.Leadership, -500, 11, -100)]
    [Arguments(GamePointKind.Honor, 0, 0, 0)]
    [Arguments(GamePointKind.Honor, int.MaxValue, 0, int.MaxValue - 1000)]
    public async Task CurrencyChangeEmitsOneNativeDeltaBeforeOneAuthoritativeBalance(
        GamePointKind kind, int requested, int wireSlot, int effectiveDelta)
    {
        var sent = new List<byte[]>();
        var session = Mock.Of<ISession>();
        session.SendPacket(Any<byte[]>()).Callback((byte[] bytes) => sent.Add(bytes));
        var connection = new GameConnection(session.Object);
        var character = new Character(new UnitCustomModelParams())
        {
            Id = 1007, ObjId = 1059, Connection = connection,
            HonorPoint = 1000, VocationPoint = 500, LeadershipPoint = 100,
            LeadershipPeriodPoint = 777
        };
        connection.ActiveChar = character;

        var questEvents = new List<OnQuestObjectiveArgs>();
        character.Events.OnQuestObjective += (_, args) => questEvents.Add(args);

        character.ChangeGamePoints(kind, requested, applyGainModifiers: false);

        var countsForQuest = effectiveDelta > 0 && kind is GamePointKind.Honor or GamePointKind.Vocation;
        await Assert.That(questEvents.Count).IsEqualTo(countsForQuest ? 1 : 0);
        if (countsForQuest)
        {
            await Assert.That(questEvents.Single().Type).IsEqualTo(kind == GamePointKind.Honor
                ? QuestObjectiveEventType.GainHonorPoint : QuestObjectiveEventType.GainLivingPoint);
            await Assert.That(questEvents.Single().Amount).IsEqualTo(effectiveDelta);
            await Assert.That(questEvents.Single().Actor).IsEqualTo(character);
        }

        var packets = sent.Select(SentPacket.Read).ToArray();
        var deltas = packets.Where(p => p.Opcode == SCOffsets.SCGamePointChangedPacket).ToArray();
        var balances = packets.Where(p => p.Opcode == SCOffsets.SCCharacterGamePointsPacket).ToArray();
        await Assert.That(deltas.Length).IsEqualTo(1);
        await Assert.That(balances.Length).IsEqualTo(1);
        var delta = new PacketStream(deltas.Single().Body);
        await Assert.That(delta.ReadByte()).IsEqualTo((byte)1);
        await Assert.That(delta.ReadByte()).IsEqualTo((byte)wireSlot);
        await Assert.That(delta.ReadInt32()).IsEqualTo(effectiveDelta);
        await Assert.That(delta.LeftBytes).IsEqualTo(0);
        await Assert.That(Array.FindIndex(packets, p => p.Opcode == SCOffsets.SCGamePointChangedPacket))
            .IsLessThan(Array.FindIndex(packets, p => p.Opcode == SCOffsets.SCCharacterGamePointsPacket));
        var balance = new PacketStream(balances.Single().Body);
        await Assert.That(balance.ReadInt32()).IsEqualTo(kind == GamePointKind.Honor ? 1000 + effectiveDelta : 1000);
        await Assert.That(balance.ReadInt32()).IsEqualTo(kind == GamePointKind.Vocation ? 500 + effectiveDelta : 500);
        for (var i = 2; i < 11; i++) balance.ReadInt32();
        await Assert.That(balance.ReadInt32()).IsEqualTo(kind == GamePointKind.Leadership ? 100 + effectiveDelta : 100);
        await Assert.That(balance.ReadInt32()).IsEqualTo(777);
    }
}
