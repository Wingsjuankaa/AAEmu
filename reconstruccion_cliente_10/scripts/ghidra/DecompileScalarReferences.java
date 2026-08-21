// Read-only Ghidra helper: decompile functions containing an instruction operand
// whose scalar value equals the requested hexadecimal value.
// Usage: -postScript DecompileScalarReferences.java c8 [startAddress endAddress [namesOnly]]
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.scalar.Scalar;

import java.util.LinkedHashSet;
import java.util.Set;

public class DecompileScalarReferences extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1 && args.length != 3 && args.length != 4) {
            printerr("Expected scalar value and optional hexadecimal function range");
            return;
        }

        long requested = Long.parseUnsignedLong(args[0].replaceFirst("^0[xX]", ""), 16);
        long rangeStart = args.length >= 3
            ? Long.parseUnsignedLong(args[1].replaceFirst("^0[xX]", ""), 16)
            : 0;
        long rangeEnd = args.length >= 3
            ? Long.parseUnsignedLong(args[2].replaceFirst("^0[xX]", ""), 16)
            : -1L;
        Set<Function> functions = new LinkedHashSet<>();
        var instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            boolean matched = false;
            for (int operand = 0; operand < instruction.getNumOperands() && !matched; operand++) {
                for (Object object : instruction.getOpObjects(operand)) {
                    if (object instanceof Scalar scalar && scalar.getUnsignedValue() == requested) {
                        Function function = getFunctionContaining(instruction.getAddress());
                        long entry = function == null ? 0 : function.getEntryPoint().getOffset();
                        if (function != null &&
                            (args.length < 3 ||
                             Long.compareUnsigned(entry, rangeStart) >= 0 &&
                             Long.compareUnsigned(entry, rangeEnd) < 0)) {
                            functions.add(function);
                        }
                        matched = true;
                        break;
                    }
                }
            }
        }

        println("MATCHED_FUNCTIONS " + functions.size());
        if (args.length == 4 && args[3].equalsIgnoreCase("namesOnly")) {
            for (Function function : functions) {
                println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint());
            }
            return;
        }
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (Function function : functions) {
                println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint());
                DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
                if (result.decompileCompleted()) {
                    println(result.getDecompiledFunction().getC());
                } else {
                    printerr("Failed to decompile " + function.getName() + ": " + result.getErrorMessage());
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
