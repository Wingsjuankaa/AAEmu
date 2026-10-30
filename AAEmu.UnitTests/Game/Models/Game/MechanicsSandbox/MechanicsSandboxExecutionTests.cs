using AAEmu.Game.Models.Game.MechanicsSandbox;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.GmPanel;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.NPChar;

namespace AAEmu.UnitTests.Game.Models.Game.MechanicsSandbox;

public class MechanicsSandboxExecutionTests
{
    [Test]
    public async Task UnregisteredActors_KeepTheOrdinaryExecutionPath()
    {
        var actor = new object();
        bool allowed, callbackAllowed;
        MechanicsSandboxExecution.Stamp stamp;
        using (var lease = MechanicsSandboxExecution.EnterCurrent(actor))
        { allowed = lease.Allowed; stamp = lease.Stamp; }
        using (var callback = MechanicsSandboxExecution.EnterScheduled(actor, default))
            callbackAllowed = callback.Allowed;
        await Assert.That(allowed).IsTrue();
        await Assert.That(callbackAllowed).IsTrue();
        await Assert.That(stamp.Owner).IsNull();
    }

    [Test]
    public async Task Reset_RetiresEveryPreviousCallback_AndAdmitsANewAttempt()
    {
        var actor = new object();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(actor);
        var old = MechanicsSandboxExecution.Capture(actor);
        scope.BeginReset();
        bool duringReset;
        using (var whileResetting = MechanicsSandboxExecution.EnterCurrent(actor))
            duringReset = whileResetting.Allowed;
        scope.CompleteReset();
        bool staleAllowed, currentAllowed;
        long generation;
        using (var stale = MechanicsSandboxExecution.EnterScheduled(actor, old))
            staleAllowed = stale.Allowed;
        using (var current = MechanicsSandboxExecution.EnterCurrent(actor))
        { currentAllowed = current.Allowed; generation = current.Stamp.Generation; }
        await Assert.That(duringReset).IsFalse();
        await Assert.That(staleAllowed).IsFalse();
        await Assert.That(currentAllowed).IsTrue();
        await Assert.That(generation > old.Generation).IsTrue();
    }

    [Test]
    public async Task Reset_DoesNotBlockAnUnrelatedActor()
    {
        var mine = new object();
        var other = new object();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(mine);
        scope.BeginReset();
        bool allowed;
        using (var callback = MechanicsSandboxExecution.EnterScheduled(other, default))
            allowed = callback.Allowed;
        await Assert.That(allowed).IsTrue();
    }

    [Test]
    public async Task RetryingAFailedRestore_RetiresItsPartiallyCreatedCallbacks()
    {
        var actor = new object();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(actor);
        scope.BeginReset();
        var partial = MechanicsSandboxExecution.Capture(actor);
        scope.BeginReset();
        var allowed = true;
        scope.Mutate(() =>
        {
            using var stale = MechanicsSandboxExecution.EnterScheduled(actor, partial);
            allowed = stale.Allowed;
        });
        scope.CompleteReset();
        await Assert.That(allowed).IsFalse();
    }

    [Test]
    public async Task ClosingAndRebindingActor_DoesNotMakeAnOldCallbackValidAgain()
    {
        var actor = new object();
        var oldScope = new MechanicsSandboxExecution.Scope();
        oldScope.AddActor(actor);
        var old = MechanicsSandboxExecution.Capture(actor);
        oldScope.Dispose();
        using var newScope = new MechanicsSandboxExecution.Scope();
        newScope.AddActor(actor);
        bool staleAllowed, currentAllowed;
        using (var stale = MechanicsSandboxExecution.EnterScheduled(actor, old))
            staleAllowed = stale.Allowed;
        using (var current = MechanicsSandboxExecution.EnterCurrent(actor))
            currentAllowed = current.Allowed;
        await Assert.That(staleAllowed).IsFalse();
        await Assert.That(currentAllowed).IsTrue();
    }

    [Test]
    public async Task Reset_WaitsForAnEffectAlreadyExecutingBeforeRetiringItsEpoch()
    {
        var actor = new object();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(actor);
        using var effectEntered = new ManualResetEventSlim();
        using var releaseEffect = new ManualResetEventSlim();
        using var resetAttempted = new ManualResetEventSlim();
        var running = Task.Run(() =>
        {
            using var lease = MechanicsSandboxExecution.EnterCurrent(actor);
            effectEntered.Set();
            if (!releaseEffect.Wait(TimeSpan.FromSeconds(5)))
                throw new TimeoutException("Test effect was not released.");
        });
        Task reset = null;
        try
        {
            if (!effectEntered.Wait(TimeSpan.FromSeconds(5)))
                throw new TimeoutException("Test effect did not enter.");
            reset = Task.Run(() => { resetAttempted.Set(); scope.BeginReset(); });
            if (!resetAttempted.Wait(TimeSpan.FromSeconds(5)))
                throw new TimeoutException("Test reset did not start.");
            await Assert.That(reset.IsCompleted).IsFalse();
        }
        finally
        {
            releaseEffect.Set();
            await running.WaitAsync(TimeSpan.FromSeconds(5));
            if (reset != null)
                await reset.WaitAsync(TimeSpan.FromSeconds(5));
        }
    }

    [Test]
    public async Task OldProjectileTask_CannotReleaseTheTimelineOfAReusedSkill()
    {
        var caster = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var skill = new Skill { SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster), TlId = 31 };
        var projectile = new ApplySkillTask(skill, caster, null, caster, null, null);
        scope.BeginReset();
        scope.CompleteReset();
        // Same reusable auto-attack Skill, now carrying the next cast's timeline and cancellation flag.
        skill.SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster);
        skill.TlId = 72;
        skill.Cancelled = true;
        projectile.Execute();
        await Assert.That(skill.TlId).IsEqualTo((ushort)72);
    }

    [Test]
    public async Task OldPlotEvent_AfterResetCannotApplyItsEffects()
    {
        var caster = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var skill = new Skill { SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster) };
        var state = new PlotState(caster, null, caster, null, null, skill);
        scope.BeginReset();
        scope.CompleteReset();
        // Event and target are deliberately absent: the stale gate must precede effect/packet consumers.
        new PlotNode().Execute(state, null);
        await Assert.That(state.CancellationRequested()).IsTrue();
    }

    [Test]
    public async Task OldPlotStartup_CannotOverwriteTheNewAttemptsPlotSlot()
    {
        var caster = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var staleSkill = new Skill { SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster) };
        scope.BeginReset();
        scope.CompleteReset();
        var current = new PlotState(caster, null, caster, null, null, new Skill());
        caster.ActivePlotState = current;
        await new global::AAEmu.Game.Models.Game.Skills.Plots.Plot().RunAsync(
            caster, null, caster, null, null, staleSkill);
        await Assert.That(ReferenceEquals(caster.ActivePlotState, current)).IsTrue();
    }

    [Test]
    public async Task OldCastChannelAndChildTasks_CannotStartNativeLifecycleForAReusedSkill()
    {
        var caster = new Character(null);
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var skill = new Skill { SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster), TlId = 31 };
        global::AAEmu.Game.Models.Tasks.Task[] tasks =
        [
            new CastTask(skill, caster, null, caster, null, null),
            new EndChannelingTask(skill, caster, null, caster, null, null, null),
            new ChannelingTickTask(skill, caster),
            new UseSkillTask(skill, caster, null, caster, null, null),
            new UseAutoAttackSkillTask(skill, caster)
        ];
        scope.BeginReset();
        scope.CompleteReset();
        skill.SandboxExecutionStamp = MechanicsSandboxExecution.Capture(caster);
        skill.TlId = 72;
        skill.Cancelled = false;
        foreach (var task in tasks)
            task.Execute();
        // None may dereference this deliberately absent Template, emit native start/end, or touch the new timeline.
        await Assert.That(skill.TlId).IsEqualTo((ushort)72);
        await Assert.That(skill.Cancelled).IsFalse();
    }

    [Test]
    public async Task DelayedTimeoutAndRepeatedEffects_FromThePreviousAttemptCannotMutateTheNewOne()
    {
        var caster = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var damage = 0;
        var timeout = new BuffTriggerTask(() => damage += 7, caster);
        var repeated = new SpecialEffectRepeatTask(() => damage += 11, caster);
        scope.BeginReset();
        scope.CompleteReset();
        timeout.Execute();
        repeated.Execute();
        await Assert.That(damage).IsEqualTo(0);
        new BuffTriggerTask(() => damage += 3, caster).Execute();
        await Assert.That(damage).IsEqualTo(3);
        new SpecialEffectRepeatTask(() => damage += 5).Execute();
        await Assert.That(damage).IsEqualTo(8);
    }

    [Test]
    public async Task SandboxCommand_HasSpanishEditorialMetadataAndAReadOnlyExample()
    {
        var metadata = GmPanelDescriptions.Get("MechanicsSandbox");
        await Assert.That(GmPanelDescriptions.Has("MechanicsSandbox")).IsTrue();
        await Assert.That(metadata.Category).IsEqualTo("debug");
        await Assert.That(metadata.Example).IsEqualTo("status");
    }

    [Test]
    public async Task OldPeriodicBuffCallbacks_CannotTickOrRescheduleAfterReset()
    {
        var caster = new Unit();
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        var buff = new Buff(caster, caster, null, new BuffTemplate { Tick = 1000 }, null, DateTime.UtcNow);
        var dot = new DispelTask(buff);
        var aura = new AuraTask(buff);
        scope.BeginReset();
        scope.CompleteReset();
        dot.Execute();
        aura.Execute();
        await Assert.That(buff.State).IsEqualTo(EffectState.Created);
        await Assert.That(buff.TickIndex).IsEqualTo(0u);
    }

    [Test]
    public async Task OldCraftAndDespawnCallbacks_CannotTouchTheNextAttemptsState()
    {
        var caster = new Character(null);
        var npc = new Npc { ObjId = 72 };
        using var scope = new MechanicsSandboxExecution.Scope();
        scope.AddActor(caster);
        scope.AddActor(npc);
        var craft = new CraftTask(caster, 1, 0, 1);
        var despawn = new DespawnTask(npc);
        scope.BeginReset();
        scope.CompleteReset();
        // No initialized Craft/World services: stale tasks must not reach any real consumer at all.
        craft.Execute();
        despawn.Execute();
        await Assert.That(npc.ObjId).IsEqualTo(72u);
    }
}
