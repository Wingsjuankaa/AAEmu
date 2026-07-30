// Find exact AA8 strings and decompile every direct referencing function.
// Usage: DumpAa8ExactStringConsumers.java <output> <exact-string> [...]
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
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.util.DefinedDataIterator;

public class DumpAa8ExactStringConsumers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output file and at least one exact string");
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
            out.println("FORMAT\tAA8_EXACT_STRING_CONSUMERS_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());

            for (int index = 1; index < args.length; index++) {
                String needle = args[index];
                int matchCount = 0;
                Set<Address> dumpedFunctions = new HashSet<>();
                out.println();
                out.println("EXACT\t" + needle);

                for (Data data : DefinedDataIterator.byDataInstance(
                         currentProgram,
                         candidate -> candidate.getValue() instanceof String)) {
                    if (!needle.equals(String.valueOf(data.getValue()))) {
                        continue;
                    }
                    matchCount++;
                    out.println("STRING\t" + data.getAddress());
                    ReferenceIterator references = currentProgram
                        .getReferenceManager().getReferencesTo(data.getAddress());
                    while (references.hasNext()) {
                        Reference reference = references.next();
                        Function function =
                            listing.getFunctionContaining(reference.getFromAddress());
                        out.println(
                            "REFERENCE\t" + reference.getFromAddress() + "\t" +
                            reference.getReferenceType() + "\t" +
                            (function == null
                                ? "<none>"
                                : function.getName() + "@" +
                                  function.getEntryPoint()));
                        if (function == null ||
                            !dumpedFunctions.add(function.getEntryPoint())) {
                            continue;
                        }
                        out.println(
                            "FUNCTION_BEGIN\t" + function.getName() + "\t" +
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
                        out.println("FUNCTION_END");
                    }
                }
                out.println("STRING_MATCHES\t" + matchCount);
            }
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
