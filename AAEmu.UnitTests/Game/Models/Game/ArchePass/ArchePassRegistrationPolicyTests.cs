using AAEmu.Game.Models.Game.ArchePass;

namespace AAEmu.UnitTests.Game.Models.Game.ArchePass;

public class ArchePassRegistrationPolicyTests
{
    [Test]
    public async Task RetailBookIsNotFullBeforeSixRegisteredPasses()
    {
        var statuses = Enumerable.Repeat(ArchePassStatus.Owned, 5);

        await Assert.That(ArchePassRegistrationPolicy.IsFull(statuses)).IsFalse();
    }

    [Test]
    public async Task RetailBookIsFullAtSixRegisteredPasses()
    {
        var statuses = Enumerable.Repeat(ArchePassStatus.Owned, 6);

        await Assert.That(ArchePassRegistrationPolicy.IsFull(statuses)).IsTrue();
    }

    [Test]
    public async Task TerminalStatusesDoNotConsumeRegistrationCapacity()
    {
        ArchePassStatus[] statuses =
        [
            ArchePassStatus.Owned,
            ArchePassStatus.Progress,
            ArchePassStatus.Expired,
            ArchePassStatus.Dropped,
            ArchePassStatus.Completed
        ];

        await Assert.That(ArchePassRegistrationPolicy.IsFull(statuses)).IsFalse();
    }

    [Test]
    public async Task PersistenceAllowsSixRegisteredPassesWithOneActive()
    {
        ArchePassStatus[] statuses =
        [
            ArchePassStatus.Progress,
            ArchePassStatus.Owned,
            ArchePassStatus.Owned,
            ArchePassStatus.Owned,
            ArchePassStatus.Owned,
            ArchePassStatus.Owned
        ];

        await Assert.That(ArchePassRegistrationPolicy.HasValidPersistenceState(statuses)).IsTrue();
    }

    [Test]
    public async Task PersistenceRejectsMoreThanSixRegisteredPasses()
    {
        var statuses = Enumerable.Repeat(ArchePassStatus.Owned, 7);

        await Assert.That(ArchePassRegistrationPolicy.HasValidPersistenceState(statuses)).IsFalse();
    }

    [Test]
    public async Task PersistenceRejectsMoreThanOneActivePass()
    {
        ArchePassStatus[] statuses = [ArchePassStatus.Progress, ArchePassStatus.Progress];

        await Assert.That(ArchePassRegistrationPolicy.HasValidPersistenceState(statuses)).IsFalse();
    }

    [Test]
    public async Task ActivatingAnOwnedPassPausesTheCurrentPassWithoutResettingProgress()
    {
        var current = CreateState(88, ArchePassStatus.Progress, point: 3500, premium: true, normalTier: 3);
        var target = CreateState(19, ArchePassStatus.Owned, point: 120, premium: false, normalTier: 1);
        IReadOnlyDictionary<int, CharacterArchePassState> states = new Dictionary<int, CharacterArchePassState>
        {
            [current.Type] = current,
            [target.Type] = target
        };

        var changed = ArchePassRegistrationPolicy.TryActivate(
            states, target.Type, out var paused, out var started);

        await Assert.That(changed).IsTrue();
        await Assert.That(paused).IsSameReferenceAs(current);
        await Assert.That(started).IsSameReferenceAs(target);
        await Assert.That(current.Status).IsEqualTo(ArchePassStatus.Owned);
        await Assert.That(current.Point).IsEqualTo(3500);
        await Assert.That(current.Premium).IsTrue();
        await Assert.That(current.LastRewardTier).IsEqualTo(3);
        await Assert.That(target.Status).IsEqualTo(ArchePassStatus.Progress);
        await Assert.That(target.Point).IsEqualTo(120);
        await Assert.That(ArchePassRegistrationPolicy.HasValidPersistenceState(
            states.Values.Select(state => state.Status))).IsTrue();
    }

    [Test]
    public async Task ActivatingTheOnlyOwnedPassCreatesOneActivePass()
    {
        var target = CreateState(19, ArchePassStatus.Owned);
        IReadOnlyDictionary<int, CharacterArchePassState> states =
            new Dictionary<int, CharacterArchePassState> { [target.Type] = target };

        var changed = ArchePassRegistrationPolicy.TryActivate(
            states, target.Type, out var paused, out var started);

        await Assert.That(changed).IsTrue();
        await Assert.That(paused).IsNull();
        await Assert.That(started).IsSameReferenceAs(target);
        await Assert.That(target.Status).IsEqualTo(ArchePassStatus.Progress);
    }

    [Test]
    public async Task ActivatingANonOwnedPassIsRejectedWithoutMutation()
    {
        var current = CreateState(88, ArchePassStatus.Progress, point: 3500);
        var target = CreateState(19, ArchePassStatus.Completed, point: 120);
        IReadOnlyDictionary<int, CharacterArchePassState> states = new Dictionary<int, CharacterArchePassState>
        {
            [current.Type] = current,
            [target.Type] = target
        };

        var changed = ArchePassRegistrationPolicy.TryActivate(
            states, target.Type, out var paused, out var started);

        await Assert.That(changed).IsFalse();
        await Assert.That(paused).IsNull();
        await Assert.That(started).IsNull();
        await Assert.That(current.Status).IsEqualTo(ArchePassStatus.Progress);
        await Assert.That(target.Status).IsEqualTo(ArchePassStatus.Completed);
    }

    private static CharacterArchePassState CreateState(
        int type,
        ArchePassStatus status,
        long point = 0,
        bool premium = false,
        int normalTier = 0) => new()
    {
        Type = type,
        Status = status,
        Point = point,
        Premium = premium,
        LastRewardTier = normalTier
    };
}
