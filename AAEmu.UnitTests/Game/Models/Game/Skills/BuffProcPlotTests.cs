using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Plots;
using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using AAEmu.Game.Models.Game.Skills.Templates;

namespace AAEmu.UnitTests.Game.Models.Game.Skills;

public class BuffProcPlotTests
{
    [Test]
    [Arguments(true, false)]
    [Arguments(false, true)]
    public async Task RepeatedInstantBuffProc_PreservesCastingAndChanneling(bool casting, bool channeling)
    {
        var owner = new Character(null);
        var original = new Skill(new SkillTemplate { Id = 101 });
        var active = new PlotState(owner, null, owner, null, null, original)
            { IsCasting = casting, IsChanneling = channeling };
        owner.ActivePlotState = active;
        for (var i = 0; i < 5; i++)
        {
            var proc = new Skill(new SkillTemplate
                { Id = 202, SkipValidateSource = true, IgnoreGlobalCooldown = true })
                { IsBuffTriggered = true };
            var background = Plot.BindState(owner, null, owner, null, null, proc);
            await Assert.That(ReferenceEquals(owner.ActivePlotState, active)).IsTrue();
            await Assert.That(active.CancellationRequested()).IsFalse();
            await Assert.That(ReferenceEquals(proc.ActivePlotState, background)).IsTrue();
            background.RequestCancellation();
            await Assert.That(active.CancellationRequested()).IsFalse();
        }
    }

    [Test]
    [Arguments(false, true, true, 0)]
    [Arguments(true, false, true, 0)]
    [Arguments(true, true, false, 0)]
    [Arguments(true, true, true, 1000)]
    public async Task OrdinaryOrCastTimeSkill_DoesNotBecomeBackground(bool buff, bool skip, bool ignore, int casting)
    {
        var skill = new Skill(new SkillTemplate
            { SkipValidateSource = skip, IgnoreGlobalCooldown = ignore, CastingTime = casting })
            { IsBuffTriggered = buff };
        await Assert.That(skill.IsBackgroundProc).IsFalse();
    }
}
