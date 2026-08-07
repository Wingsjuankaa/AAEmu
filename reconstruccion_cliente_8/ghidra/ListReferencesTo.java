// List every static reference to one or more virtual addresses.
// Usage: ListReferencesTo.java <address> [<address> ...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class ListReferencesTo extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected at least one virtual address");
        }

        for (String rawAddress : args) {
            Address target = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(rawAddress);
            println("=== REFERENCES_TO " + target + " ===");
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(target);
            int count = 0;
            while (references.hasNext()) {
                Reference reference = references.next();
                Address from = reference.getFromAddress();
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(from);
                String owner = function == null
                    ? "NO_FUNCTION"
                    : function.getName() + "@" + function.getEntryPoint();
                println(from + " " + reference.getReferenceType() + " " + owner);
                count++;
            }
            println("=== REFERENCE_COUNT " + count + " ===");
        }
    }
}
