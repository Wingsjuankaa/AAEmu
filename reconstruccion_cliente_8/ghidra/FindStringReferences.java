// Find defined strings containing one or more fragments and list their references.
// Usage: FindStringReferences.java <fragment> [<fragment> ...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class FindStringReferences extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected at least one string fragment");
        }

        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        for (String rawFragment : args) {
            String fragment = rawFragment.toLowerCase();
            println("=== STRINGS_MATCHING " + rawFragment + " ===");
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
                String text = value == null ? "" : value.toString();
                if (!text.toLowerCase().contains(fragment)) {
                    continue;
                }
                println("STRING " + data.getAddress() + " " + text);
                strings++;
                ReferenceIterator refs = currentProgram.getReferenceManager()
                    .getReferencesTo(data.getAddress());
                while (refs.hasNext()) {
                    Reference reference = refs.next();
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
