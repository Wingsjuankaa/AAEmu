// Decompile explicit AA8 functions together with their direct callers.
// Usage: DumpAa8CallGraph.java <output> <caller-depth> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpAa8CallGraph extends GhidraScript {
    private PrintWriter out;
    private DecompInterface decompiler;
    private final Set<Address> dumped = new HashSet<>();

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Expected: output file, caller depth, and at least one address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        int depth = Integer.parseInt(args[1]);
        out = new PrintWriter(output, StandardCharsets.UTF_8.name());
        decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try {
            out.println("PROGRAM " + currentProgram.getName());
            out.println("IMAGE_BASE " + currentProgram.getImageBase());
            for (int index = 2; index < args.length; index++) {
                dumpFunctionAndCallers(
                    toAddr(args[index]), depth, "requested target " + args[index]);
            }
        } finally {
            decompiler.dispose();
            out.close();
        }

        println("Wrote " + output.getAbsolutePath());
    }

    private void dumpFunctionAndCallers(
        Address address, int callerDepth, String reason) {
        Listing listing = currentProgram.getListing();
        Function function = listing.getFunctionContaining(address);
        if (function == null) {
            function = listing.getFunctionAt(address);
        }
        if (function == null) {
            out.println("NO FUNCTION at " + address + " (" + reason + ")");
            return;
        }

        dumpFunction(function, reason);
        if (callerDepth <= 0) {
            return;
        }

        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        while (references.hasNext()) {
            Reference reference = references.next();
            if (!reference.getReferenceType().isCall()) {
                continue;
            }

            Function caller = listing.getFunctionContaining(reference.getFromAddress());
            if (caller != null) {
                dumpFunctionAndCallers(
                    caller.getEntryPoint(),
                    callerDepth - 1,
                    "caller of " + function.getName() +
                    " from " + reference.getFromAddress());
            }
        }
    }

    private void dumpFunction(Function function, String reason) {
        if (!dumped.add(function.getEntryPoint())) {
            return;
        }

        out.println();
        out.println("===== " + function.getName() + " @ " +
            function.getEntryPoint() + " =====");
        out.println("REASON " + reason);

        DecompileResults result =
            decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() ||
            result.getDecompiledFunction() == null) {
            out.println("DECOMPILE FAILED: " + result.getErrorMessage());
            return;
        }

        out.println(result.getDecompiledFunction().getC());
    }
}
