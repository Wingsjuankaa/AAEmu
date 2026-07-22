using AAEmu.Game.Models.Game.Skills.Plots.Tree;
using Xunit;

namespace AAEmu.Tests
{
    public class PlotVariableOperationsTests
    {
        [Fact]
        public void BladeFlurryTargetCountEnablesControllerClosingBranch()
        {
            var state = new PlotState(null, null, null, null, null, null)
            {
                CurrentTargetCount = 1
            };

            // Swiftblade event 37729: A = Targets + 0.
            Assert.True(PlotVariableOperations.TrySet(state, 1, 0, 12));
            Assert.Equal(1, state.Variables[1]);

            // Swiftblade event 38516: A >= 1.
            Assert.True(PlotVariableOperations.TryResolve(state, 1, out var value));
            Assert.True(PlotVariableOperations.TryCompare(value, 3, 1, out var result));
            Assert.True(result);
        }

        [Fact]
        public void VariableAssignmentSupportsLiteralAndRelativeOperands()
        {
            var state = new PlotState(null, null, null, null, null, null);

            Assert.True(PlotVariableOperations.TrySet(state, 1, 4, 11)); // A = Zero + 4
            Assert.True(PlotVariableOperations.TrySet(state, 1, -1, 1)); // A = A - 1
            Assert.Equal(3, state.Variables[1]);
        }

        [Theory]
        [InlineData(4, 1, 4, true)]
        [InlineData(4, 2, 3, true)]
        [InlineData(4, 3, 4, true)]
        [InlineData(4, 4, 5, true)]
        [InlineData(4, 5, 4, true)]
        public void ConfirmedComparisonOperatorsAreEvaluated(int value, int operation, int compareValue, bool expected)
        {
            Assert.True(PlotVariableOperations.TryCompare(value, operation, compareValue, out var result));
            Assert.Equal(expected, result);
        }
    }
}
