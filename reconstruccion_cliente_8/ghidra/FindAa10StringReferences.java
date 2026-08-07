// Find defined strings containing one or more fragments and list their owners.
// Kept under a dedicated class name so AA10 headless runs cannot reuse a
// stale Ghidra script class compiled by a different JDK.
// Usage: FindAa10StringReferences.java <fragment> [<fragment> ...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class FindAa10StringReferences extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected at least one string fragment");
        }

        Listing listing = currentProgram.getListing();
        for (String rawFragment : args) {
            String fragment = rawFragment.toLowerCase();
            println("=== AA10_STRINGS_MATCHING " + rawFragment + " ===");
            int strings = 0;
            int references = 0;
            for (Data data : listing.getDefinedData(true)) {
                if (monitor.isCancelled()) {
                    break;
                }
                if (!data.hasStringValue()) {
                    continue;
                }
                Object value = data.getValue();
                String candidate = value == null ? "" : value.toString();
                if (!candidate.toLowerCase().contains(fragment)) {
                    continue;
                }
                println("STRING " + data.getAddress() + " " + candidate);
                strings++;
                ReferenceIterator iterator = currentProgram.getReferenceManager()
                    .getReferencesTo(data.getAddress());
                while (iterator.hasNext()) {
                    Reference reference = iterator.next();
                    Function owner = currentProgram.getFunctionManager()
                        .getFunctionContaining(reference.getFromAddress());
                    String function = owner == null
                        ? "NO_FUNCTION"
                        : owner.getName() + "@" + owner.getEntryPoint();
                    println("  REF " + reference.getFromAddress() + " " +
                        reference.getReferenceType() + " " + function);
                    references++;
                }
            }
            println("=== STRING_COUNT " + strings + " REFERENCE_COUNT " + references + " ===");
        }
    }
}
