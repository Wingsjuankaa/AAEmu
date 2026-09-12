using System.Reflection;
using AAEmu.Commons.Utils;
using AAEmu.Game.GameData;
using AAEmu.Game.Models.Game.Char;
using AAEmu.Game.Models.Game.DoodadObj.Funcs;
using AAEmu.Game.Models.Game.Quests;
using AAEmu.Game.Models.Game.Quests.Static;
using AAEmu.Game.Models.Game.Quests.Templates;
using Microsoft.Data.Sqlite;

namespace AAEmu.UnitTests.Game.Models.Game.DoodadObj;

[NotInParallel]
public class DoodadQuestStartRequirementsTests
{
    private static readonly FieldInfo Instance = typeof(Singleton<UnitRequirementsGameData>)
        .GetField("s_instance", BindingFlags.Static | BindingFlags.NonPublic)!;
    private object _previous;

    [Before(Test)]
    public void Setup()
    {
        _previous = Instance.GetValue(null);
        using var db = new SqliteConnection("Data Source=:memory:");
        db.Open();
        using var command = db.CreateCommand();
        // Native full/compact r575 row 67247: 9565 requires completion of 9564.
        command.CommandText = """
            CREATE TABLE unit_reqs(id INTEGER, owner_id INTEGER, owner_type TEXT,
                kind_id INTEGER, value1 INTEGER, value2 INTEGER, enable TEXT,
                value3 INTEGER, display_msg TEXT);
            INSERT INTO unit_reqs VALUES(67247,41750,'QuestComponent',31,9564,0,'t',0,'t');
            """;
        command.ExecuteNonQuery();
        var requirements = new UnitRequirementsGameData();
        requirements.Load(db);
        Instance.SetValue(null, requirements);
    }

    [After(Test)]
    public void Cleanup() => Instance.SetValue(null, _previous);

    private static QuestTemplate AncientArtifact()
    {
        var template = new QuestTemplate { Id = 9565, MinLevel = 55 };
        template.Components.Add(41750, new QuestComponentTemplate(template)
        {
            Id = 41750, KindId = QuestComponentKind.Start
        });
        return template;
    }

    private static Character Player()
    {
        var character = new Character(null) { Id = 1007, Level = 55, Race = Race.Nuian };
        character.Quests = new CharacterQuests(character);
        return character;
    }

    [Test]
    public async Task ArtifactIsNotOfferedBeforePreviousQuestIsCompleted()
    {
        var player = Player();
        var template = AncientArtifact();
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsFalse();
        await Assert.That(player.Quests.ActiveQuests.Count).IsEqualTo(0);
        await Assert.That(player.Quests.HasQuestCompleted(9564)).IsFalse();

        player.Quests.SetCompletedQuestFlag(9564, true);
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsTrue();
        await Assert.That(player.Quests.ActiveQuests.Count).IsEqualTo(0);
        await Assert.That(player.Quests.HasQuestCompleted(9565)).IsFalse();
    }

    [Test]
    public async Task UnavailableFirstOfferDoesNotHideLaterEligibleOffer()
    {
        var player = Player();
        var later = new QuestTemplate { Id = 10930, MinLevel = 55 };
        QuestTemplate[] candidates = [AncientArtifact(), later];
        var selected = candidates.FirstOrDefault(t => DoodadFuncQuest.IsEligible(1, player, t));
        await Assert.That(selected).IsSameReferenceAs(later);
    }

    [Test]
    public async Task StartRequirementsAlsoRespectLevelRaceAndCompletion()
    {
        var player = Player();
        player.Quests.SetCompletedQuestFlag(9564, true);
        var template = AncientArtifact();
        template.MinLevel = 56;
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsFalse();
        template.MinLevel = 55;
        template.RaceMask = 8; // Elf only
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsFalse();
        template.RaceMask = 255;
        player.Quests.SetCompletedQuestFlag(9565, true);
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsFalse();
        template.Repeatable = true;
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsTrue();
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, null!)).IsFalse();
    }

    [Test]
    public async Task ReportsDoNotRecheckAcceptanceRequirements()
    {
        var player = Player();
        var template = AncientArtifact();
        // The report selector needs only active membership; it does not execute the Quest.
        player.Quests.ActiveQuests.Add(template.Id, null!);
        await Assert.That(DoodadFuncQuest.IsEligible(2, player, template)).IsTrue();
        await Assert.That(DoodadFuncQuest.IsEligible(1, player, template)).IsFalse();
    }
}
