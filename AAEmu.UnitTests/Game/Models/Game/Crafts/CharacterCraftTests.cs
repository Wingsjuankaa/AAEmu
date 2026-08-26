using System.Reflection;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.Crafts;
using AAEmu.Game.Models.Game.Skills;
using AAEmu.Game.Models.Game.Skills.Templates;
using AAEmu.Game.Models.Game.Units;

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

    private static void SetActiveCraft(CharacterCraft state, Craft craft)
    {
        typeof(CharacterCraft).GetField("_currentCraft", BindingFlags.Instance | BindingFlags.NonPublic)!
            .SetValue(state, craft);
    }
}
