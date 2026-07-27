// Report every Ghidra reference to explicit AA8 addresses without
// decompiling the containing functions. This is useful for large initializers
// where a full decompilation can take several minutes.
// Usage: DumpAa8ReferenceSites.java <output> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpAa8ReferenceSites extends GhidraScript {
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
                    Function function = listing.getFunctionContaining(from);
                    out.println(
                        "REF " + from + " " + reference.getReferenceType() +
                        " primary=" + reference.isPrimary() +
                        " function=" +
                        (function == null
                            ? "<none>"
                            : function.getName() + "@" +
                              function.getEntryPoint()));
                }
            }
        }

        println("Wrote " + output.getAbsolutePath());
    }
}
