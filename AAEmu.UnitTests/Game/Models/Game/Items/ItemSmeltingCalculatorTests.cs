using AAEmu.Game.Models.Game.Items;
using AAEmu.Game.Models.Game.Items.Services;

namespace AAEmu.UnitTests.Game.Models.Game.Items;

public class ItemSmeltingCalculatorTests
{
    [Test]
    public async Task NativeTierOneBoundaries_MapGreatSuccessSuccessAndFailure()
    {
        var definition = CreateDefinition(3_000_000, 7_000_000, 0);

        var first = ItemSmeltingCalculator.Resolve(definition, 0);
        var lastGreat = ItemSmeltingCalculator.Resolve(definition, 2_999_999);
        var firstSuccess = ItemSmeltingCalculator.Resolve(definition, 3_000_000);
        var lastSuccess = ItemSmeltingCalculator.Resolve(definition, 9_999_999);

        await Assert.That(first.Result).IsEqualTo(ItemSmeltingResult.GreatSuccess);
        await Assert.That(first.Output.Id).IsEqualTo(1u);
        await Assert.That(lastGreat.Result).IsEqualTo(ItemSmeltingResult.GreatSuccess);
        await Assert.That(firstSuccess.Result).IsEqualTo(ItemSmeltingResult.Success);
        await Assert.That(firstSuccess.Output.Id).IsEqualTo(2u);
        await Assert.That(lastSuccess.Result).IsEqualTo(ItemSmeltingResult.Success);
    }

    [Test]
    public async Task NativeTierTwoBoundaries_MapSuccessThenFailure()
    {
        var definition = CreateDefinition(0, 4_000_000, 6_000_000);

        var success = ItemSmeltingCalculator.Resolve(definition, 3_999_999);
        var failure = ItemSmeltingCalculator.Resolve(definition, 4_000_000);

        await Assert.That(success.Result).IsEqualTo(ItemSmeltingResult.Success);
        await Assert.That(success.Output.Id).IsEqualTo(2u);
        await Assert.That(failure.Result).IsEqualTo(ItemSmeltingResult.Failure);
        await Assert.That(failure.Output.Id).IsEqualTo(3u);
    }

    private static ItemSmeltingDefinition CreateDefinition(int great, int success, int failure)
    {
        var definition = new ItemSmeltingDefinition
        {
            Id = 5,
            Probability = new ItemSmeltingProbability
            {
                Id = 3,
                GreatSuccess = great,
                Success = success,
                Failure = failure
            }
        };
        definition.Outputs.Add(new ItemSmeltingOutput { Id = 1, ItemId = 43445, GradeId = 0 });
        definition.Outputs.Add(new ItemSmeltingOutput { Id = 2, ItemId = 43476, GradeId = 2 });
        definition.Outputs.Add(new ItemSmeltingOutput { Id = 3, ItemId = 43483, GradeId = 3 });
        return definition;
    }
}
