// Decompile an explicit list of AA8 x2game addresses.
// Usage: DumpAa8Functions.java <output> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DumpAa8Functions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output file path and at least one function address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM " + currentProgram.getName());
            out.println("IMAGE_BASE " + currentProgram.getImageBase());

            for (int i = 1; i < args.length; i++) {
                Address address = toAddr(args[i]);
                Function function = currentProgram.getListing()
                    .getFunctionContaining(address);
                if (function == null) {
                    out.println();
                    out.println("NO FUNCTION at " + address);
                    continue;
                }

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
