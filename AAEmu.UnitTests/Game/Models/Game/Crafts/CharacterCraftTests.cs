using System.Reflection;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;
using AAEmu.Game.Models.Tasks.Skills;

namespace AAEmu.UnitTests.Game.Models.Game.Crafts;

public class CharacterCraftTests
{
    [Test]
    public async Task Cancel_WithMatchingCraftSkill_ReleasesSessionAndCancelsConsumption()
    {
        var character = new Character(new UnitCustomModelParams());
        var state = new CharacterCraft(character);
        var skill = new Skill(new SkillTemplate { Id = 40812 });
        SetActiveCraft(state, new Craft { Id = 12176, SkillId = 40812 });

        var cancelled = state.Cancel(skill);

        await Assert.That(cancelled).IsTrue();
        await Assert.That(state.IsCrafting).IsFalse();
        await Assert.That(skill.Cancelled).IsTrue();
        await Assert.That(skill.SkipAutomaticItemConsumption).IsTrue();
    }

    [Test]
    public async Task Cancel_WithUnrelatedSkill_PreservesActiveCraftSession()
    {
        var character = new Character(new UnitCustomModelParams());
        var state = new CharacterCraft(character);
        var skill = new Skill(new SkillTemplate { Id = 34492 });
        SetActiveCraft(state, new Craft { Id = 12176, SkillId = 40812 });

        var cancelled = state.Cancel(skill);

        await Assert.That(cancelled).IsFalse();
        await Assert.That(state.IsCrafting).IsTrue();
        await Assert.That(skill.Cancelled).IsFalse();
        await Assert.That(skill.SkipAutomaticItemConsumption).IsFalse();
    }

    [Test]
    public async Task Cancel_BetweenUnitsInvalidatesPendingContinuation()
    {
        var character = new Character(new UnitCustomModelParams());
        var state = new CharacterCraft(character, (_, _) => true);
        character.Craft = state;
        SetActiveCraft(state, new Craft { Id = 12176, SkillId = 40812 });
        SetField(state, "_doodadId", 77u);
        SetField(state, "_remainingCount", 2);
        SetField(state, "_generation", 9L);
        var task = new CraftTask(character, 12176, 77, 9);
        SetField(state, "_continuationTask", task);

        state.Cancel();
        task.Execute();

        await Assert.That(state.IsCrafting).IsFalse();
        await Assert.That(state.RemainingCount).IsEqualTo(0);
        await Assert.That(state.Generation).IsEqualTo(10L);
        await Assert.That(task.Cancelled).IsTrue();
    }

    [Test]
    public async Task StaleContinuationCannotTouchNewerSession()
    {
        var character = new Character(new UnitCustomModelParams());
        var state = new CharacterCraft(character, (_, _) => true);
        character.Craft = state;
        SetActiveCraft(state, new Craft { Id = 12176, SkillId = 40812 });
        SetField(state, "_doodadId", 77u);
        SetField(state, "_remainingCount", 3);
        SetField(state, "_generation", 12L);

        new CraftTask(character, 12176, 77, 11).Execute();

        await Assert.That(state.IsCrafting).IsTrue();
        await Assert.That(state.RemainingCount).IsEqualTo(3);
        await Assert.That(state.Generation).IsEqualTo(12L);
    }

    private static void SetActiveCraft(CharacterCraft state, Craft craft)
    {
        typeof(CharacterCraft).GetField("_currentCraft", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(state, craft);
    }

    private static void SetField(CharacterCraft state, string fieldName, object value) =>
        typeof(CharacterCraft).GetField(fieldName, BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(state, value);
}
