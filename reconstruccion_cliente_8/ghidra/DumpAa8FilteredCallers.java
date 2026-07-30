// Decompile direct callers of one function and retain callers containing at
// least one exact text token in their decompiled C.
// Usage: DumpAa8FilteredCallers.java <output> <target-address> <token> [...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;

public class DumpAa8FilteredCallers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Expected: output, target address and at least one token");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        Address requested = toAddr(args[1]);
        Listing listing = currentProgram.getListing();
        Function target = listing.getFunctionContaining(requested);
        if (target == null) {
            throw new IllegalArgumentException(
                "No function contains target " + requested);
        }

        List<String> tokens = new ArrayList<>();
        for (int index = 2; index < args.length; index++) {
            tokens.add(args[index]);
        }
        Set<Function> callerSet = target.getCallingFunctions(monitor);
        List<Function> callers = new ArrayList<>(callerSet);
        callers.sort(
            Comparator.comparing(
                function -> function.getEntryPoint().getOffset()));

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        int matched = 0;
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_FILTERED_CALLERS_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            out.println(
                "TARGET\t" + target.getName() + "\t" +
                target.getEntryPoint());
            out.println("CALLER_COUNT\t" + callers.size());
            for (String token : tokens) {
                out.println("FILTER_TOKEN\t" + token);
            }

            for (Function caller : callers) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result =
                    decompiler.decompileFunction(caller, 180, monitor);
                if (!result.decompileCompleted() ||
                    result.getDecompiledFunction() == null) {
                    out.println(
                        "DECOMPILE_ERROR\t" + caller.getName() + "\t" +
                        caller.getEntryPoint() + "\t" +
                        result.getErrorMessage().replace('\n', ' '));
                    continue;
                }
                String code = result.getDecompiledFunction().getC();
                List<String> hits = new ArrayList<>();
                for (String token : tokens) {
                    if (code.contains(token)) {
                        hits.add(token);
                    }
                }
                if (hits.isEmpty()) {
                    continue;
                }
                matched++;
                out.println();
                out.println(
                    "CALLER_BEGIN\t" + caller.getName() + "\t" +
                    caller.getEntryPoint());
                for (String hit : hits) {
                    out.println("TOKEN_MATCH\t" + hit);
                }
                out.println(code);
                out.println("CALLER_END");
            }
            out.println("MATCHED_CALLERS\t" + matched);
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
