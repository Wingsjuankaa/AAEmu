using AAEmu.Game.Core.Managers;
using AAEmu.Game.Models.Game.Chat;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class ChatEventJournalTests
{
    [Before(Test)]
    public void Reset() => ChatEventJournal.ClearForTests();

    [Test]
    public async Task ReadAfter_ReturnsOnlyNewerEventsInOrder()
    {
        ChatEventJournal.Record(1, "Wingsjuanka", ChatType.White, "", 142, "primero");
        ChatEventJournal.Record(1, "Wingsjuanka", ChatType.Shout, "", 142, "segundo");

        var result = ChatEventJournal.ReadAfter(1, 200);

        await Assert.That(result).HasCount().EqualTo(1);
        await Assert.That(result[0].Id).IsEqualTo(2);
        await Assert.That(result[0].Message).IsEqualTo("segundo");
        await Assert.That(result[0].Channel).IsEqualTo("Shout");
    }
}
