// Find functions containing an exact scalar operand and decompile them.
// Usage: FindAa8ScalarFunctions.java <output> <scalar>
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;

public class FindAa8ScalarFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Expected: output file path and scalar (for example 0x570)");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        long wanted = Long.decode(args[1]);
        Set<Function> matches = new LinkedHashSet<>();
        InstructionIterator instructions =
            currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            boolean found = false;
            for (int operand = 0; operand < instruction.getNumOperands() && !found; operand++) {
                for (Object object : instruction.getOpObjects(operand)) {
                    if (object instanceof Scalar &&
                        ((Scalar)object).getUnsignedValue() == wanted) {
                        found = true;
                        break;
                    }
                }
            }
            if (!found) {
                continue;
            }
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            if (function != null) {
                matches.add(function);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM " + currentProgram.getName());
            out.println("SCALAR 0x" + Long.toHexString(wanted));
            out.println("MATCHES " + matches.size());

            for (Function function : matches) {
                out.println();
                out.println("===== " + function.getName() + " @ " +
                    function.getEntryPoint() + " =====");
                DecompileResults result =
                    decompiler.decompileFunction(function, 120, monitor);
                if (!result.decompileCompleted() ||
                    result.getDecompiledFunction() == null) {
                    out.println("DECOMPILE FAILED: " + result.getErrorMessage());
                    continue;
                }
                out.println(result.getDecompiledFunction().getC());
            }
        } finally {
            decompiler.dispose();
        }

        println("Wrote " + output.getAbsolutePath());
    }
}
