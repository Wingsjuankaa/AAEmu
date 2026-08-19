using AAEmu.Game.Core.Managers;
using AAEmu.Game.Core.Managers.Id;
using AAEmu.Game.Core.Managers.World;
using AAEmu.Game.Models.Game.Mails;

namespace AAEmu.UnitTests.Game.Core.Managers;

public class MailManagerTests
{
    [Test]
    public async Task Constructor_DoesNotCallDeps()
    {
        var mockMailId = Mock.Of<IMailIdManager>();
        var mockName = Mock.Of<INameManager>();
        var mockItem = Mock.Of<IItemManager>();
        var mockTask = Mock.Of<ITaskManager>();
        var mockWorld = Mock.Of<IWorldManager>();
        var mockHousing = Mock.Of<IHousingManager>();
        var mockLocale = Mock.Of<ILocalizationManager>();
        var manager = new MailManager(mockMailId.Object, mockName.Object, mockItem.Object, mockTask.Object, mockWorld.Object, new Lazy<IHousingManager>(() => mockHousing.Object), mockLocale.Object);

        await Assert.That(manager).IsNotNull();
        Mock.VerifyNoOtherCalls(mockMailId);
        Mock.VerifyNoOtherCalls(mockName);
        Mock.VerifyNoOtherCalls(mockItem);
        Mock.VerifyNoOtherCalls(mockTask);
        Mock.VerifyNoOtherCalls(mockWorld);
        Mock.VerifyNoOtherCalls(mockHousing);
        Mock.VerifyNoOtherCalls(mockLocale);
    }

    [Test]
    public async Task DeliverPendingSpecialtyMails_ReleasesOnlyMatchingFutureRewards()
    {
        var mockWorld = Mock.Of<IWorldManager>();
        var manager = CreateManager(mockWorld.Object);
        var releaseTime = new DateTime(2026, 8, 18, 12, 0, 0, DateTimeKind.Utc);
        var matching = CreateMail(1, MailType.SysSellBackpack, releaseTime.AddHours(8));
        var otherPlayer = CreateMail(2, MailType.SysSellBackpack, releaseTime.AddHours(8));
        var otherType = CreateMail(1, MailType.Normal, releaseTime.AddHours(8));
        var alreadyAvailable = CreateMail(1, MailType.SysSellBackpack, releaseTime.AddMinutes(-1));
        manager._allPlayerMails = new Dictionary<long, BaseMail>
        {
            [1] = matching,
            [2] = otherPlayer,
            [3] = otherType,
            [4] = alreadyAvailable
        };

        var result = manager.DeliverPendingSpecialtyMails(1, releaseTime);

        await Assert.That(result.Released).IsEqualTo(1);
        await Assert.That(result.Notified).IsEqualTo(0);
        await Assert.That(matching.Body.RecvDate).IsEqualTo(releaseTime);
        await Assert.That(matching.IsDirty).IsTrue();
        await Assert.That(otherPlayer.Body.RecvDate).IsEqualTo(releaseTime.AddHours(8));
        await Assert.That(otherType.Body.RecvDate).IsEqualTo(releaseTime.AddHours(8));
        await Assert.That(alreadyAvailable.Body.RecvDate).IsEqualTo(releaseTime.AddMinutes(-1));
    }

    [Test]
    public async Task DeliverPendingSpecialtyMails_IsIdempotent()
    {
        var manager = CreateManager(Mock.Of<IWorldManager>().Object);
        var releaseTime = new DateTime(2026, 8, 18, 12, 0, 0, DateTimeKind.Utc);
        var mail = CreateMail(1, MailType.SysSellBackpack, releaseTime.AddHours(8));
        manager._allPlayerMails = new Dictionary<long, BaseMail> { [1] = mail };

        var first = manager.DeliverPendingSpecialtyMails(1, releaseTime);
        var second = manager.DeliverPendingSpecialtyMails(1, releaseTime.AddSeconds(1));

        await Assert.That(first.Released).IsEqualTo(1);
        await Assert.That(second.Released).IsEqualTo(0);
        await Assert.That(manager._allPlayerMails).Count().IsEqualTo(1);
    }

    private static MailManager CreateManager(IWorldManager worldManager)
    {
        return new MailManager(
            Mock.Of<IMailIdManager>().Object,
            Mock.Of<INameManager>().Object,
            Mock.Of<IItemManager>().Object,
            Mock.Of<ITaskManager>().Object,
            worldManager,
            new Lazy<IHousingManager>(() => Mock.Of<IHousingManager>().Object),
            Mock.Of<ILocalizationManager>().Object);
    }

    private static BaseMail CreateMail(uint receiverId, MailType type, DateTime receiveTime)
    {
        var mail = new BaseMail
        {
            MailType = type,
            ReceiverName = $"player{receiverId}",
            Header =
            {
                ReceiverId = receiverId
            },
            Body = { RecvDate = receiveTime }
        };
        mail.IsDirty = false;
        return mail;
    }
}
