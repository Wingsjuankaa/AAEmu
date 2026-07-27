// Report every Ghidra reference to explicit AA8 addresses and decompile the
// containing function when the reference originates in code.
// Usage: DumpAa8References.java <output> <address> [address...]
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

public class DumpAa8References extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output file and at least one address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        Listing listing = currentProgram.getListing();
        Set<Address> dumpedFunctions = new HashSet<>();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM " + currentProgram.getName());
            out.println("IMAGE_BASE " + currentProgram.getImageBase());

            for (int index = 1; index < args.length; index++) {
                Address target = toAddr(args[index]);
                out.println();
                out.println("===== REFERENCES TO " + target + " =====");

                ReferenceIterator references =
                    currentProgram.getReferenceManager().getReferencesTo(target);
                while (references.hasNext()) {
                    Reference reference = references.next();
                    Address from = reference.getFromAddress();
                    out.println(
                        "REF " + from + " " + reference.getReferenceType() +
                        " primary=" + reference.isPrimary());

                    Function function = listing.getFunctionContaining(from);
                    if (function == null ||
                        !dumpedFunctions.add(function.getEntryPoint())) {
                        continue;
                    }

                    out.println();
                    out.println("----- " + function.getName() + " @ " +
                        function.getEntryPoint() + " -----");
                    DecompileResults result =
                        decompiler.decompileFunction(function, 120, monitor);
                    if (!result.decompileCompleted() ||
                        result.getDecompiledFunction() == null) {
                        out.println(
                            "DECOMPILE FAILED: " + result.getErrorMessage());
                    } else {
                        out.println(result.getDecompiledFunction().getC());
                    }
                }
            }
        } finally {
            decompiler.dispose();
        }

        println("Wrote " + output.getAbsolutePath());
    }
}
