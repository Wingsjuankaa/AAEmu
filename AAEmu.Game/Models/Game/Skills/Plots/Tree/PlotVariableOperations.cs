namespace AAEmu.Game.Models.Game.Skills.Plots.Tree
{
    /// <summary>
    /// AA 8.0 plot operands are one-based: A..J are 1..10, 11 is the
    /// constant zero and 12 is the number of targets selected by the event.
    /// </summary>
    public static class PlotVariableOperations
    {
        public static bool TryResolve(PlotState state, int operand, out int value)
        {
            value = 0;
            if (state == null)
                return false;

            if (operand >= (int)PlotVariableType.A && operand <= (int)PlotVariableType.J)
            {
                value = state.Variables[operand];
                return true;
            }

            if (operand == (int)PlotVariableType.Zero)
                return true;

            if (operand == (int)PlotVariableType.Targets)
            {
                value = state.CurrentTargetCount;
                return true;
            }

            return false;
        }

        public static bool TrySet(PlotState state, int destination, int offset, int operand)
        {
            if (destination < (int)PlotVariableType.A || destination > (int)PlotVariableType.J ||
                !TryResolve(state, operand, out var sourceValue))
                return false;

            state.Variables[destination] = sourceValue + offset;
            return true;
        }

        public static bool TryCompare(int value, int operation, int compareValue, out bool result)
        {
            switch (operation)
            {
                case 1: // equal
                    result = value == compareValue;
                    return true;
                case 2: // greater than
                    result = value > compareValue;
                    return true;
                case 3: // greater than or equal
                    result = value >= compareValue;
                    return true;
                case 4: // less than
                    result = value < compareValue;
                    return true;
                case 5: // less than or equal
                    result = value <= compareValue;
                    return true;
                default:
                    result = false;
                    return false;
            }
        }
    }
}
