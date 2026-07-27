// Dump decompiled AA8 functions together with callers, callees and references.
// Usage: DumpAa8FunctionContext.java <output> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpAa8FunctionContext extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output file and at least one function address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        Listing listing = currentProgram.getListing();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_FUNCTION_CONTEXT_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());

            for (int index = 1; index < args.length; index++) {
                Address requested = toAddr(args[index]);
                Function target = listing.getFunctionContaining(requested);
                out.println();
                out.println("TARGET_REQUEST\t" + requested);
                if (target == null) {
                    out.println("TARGET_MISSING");
                    continue;
                }

                out.println(
                    "TARGET\t" + target.getName() + "\t" +
                    target.getEntryPoint());
                dumpReferences(out, target);

                List<Function> callers =
                    sorted(target.getCallingFunctions(monitor));
                out.println("CALLER_COUNT\t" + callers.size());
                for (Function caller : callers) {
                    out.println(
                        "CALLER\t" + caller.getName() + "\t" +
                        caller.getEntryPoint());
                }

                List<Function> callees =
                    sorted(target.getCalledFunctions(monitor));
                out.println("CALLEE_COUNT\t" + callees.size());
                for (Function callee : callees) {
                    out.println(
                        "CALLEE\t" + callee.getName() + "\t" +
                        callee.getEntryPoint());
                }

                Set<Address> emitted = new HashSet<>();
                dumpFunction(out, decompiler, "TARGET_DECOMPILE", target, emitted);
                for (Function caller : callers) {
                    dumpFunction(
                        out,
                        decompiler,
                        "CALLER_DECOMPILE",
                        caller,
                        emitted);
                }
                for (Function callee : callees) {
                    dumpFunction(
                        out,
                        decompiler,
                        "CALLEE_DECOMPILE",
                        callee,
                        emitted);
                }
                out.println("TARGET_END");
            }
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }

    private void dumpReferences(PrintWriter out, Function target) {
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(target.getEntryPoint());
        while (references.hasNext()) {
            Reference reference = references.next();
            Function owner = currentProgram.getListing()
                .getFunctionContaining(reference.getFromAddress());
            out.println(
                "REFERENCE\t" + reference.getFromAddress() + "\t" +
                reference.getReferenceType() + "\t" +
                (owner == null
                    ? "<none>"
                    : owner.getName() + "@" + owner.getEntryPoint()));
        }
    }

    private List<Function> sorted(Set<Function> functions) {
        List<Function> result = new ArrayList<>(functions);
        result.sort(
            Comparator.comparing(
                function -> function.getEntryPoint().getOffset()));
        return result;
    }

    private void dumpFunction(
        PrintWriter out,
        DecompInterface decompiler,
        String role,
        Function function,
        Set<Address> emitted
    ) {
        if (!emitted.add(function.getEntryPoint())) {
            return;
        }
        out.println(
            role + "_BEGIN\t" + function.getName() + "\t" +
            function.getEntryPoint());
        DecompileResults result =
            decompiler.decompileFunction(function, 180, monitor);
        if (!result.decompileCompleted() ||
            result.getDecompiledFunction() == null) {
            out.println(
                "DECOMPILE_ERROR\t" +
                result.getErrorMessage().replace('\n', ' '));
        } else {
            out.println(result.getDecompiledFunction().getC());
        }
        out.println(role + "_END");
    }
}
