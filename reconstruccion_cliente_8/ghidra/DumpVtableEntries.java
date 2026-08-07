// Dump pointer-sized entries from one or more x64 vftables.
// Usage: DumpVtableEntries.java <entry-count> <address> [<address> ...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Symbol;

public class DumpVtableEntries extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected entry-count and at least one virtual address");
        }

        int count = Integer.parseInt(args[0]);
        for (int addressIndex = 1; addressIndex < args.length; addressIndex++) {
            Address base = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(args[addressIndex]);
            println("=== VFTABLE " + base + " ENTRIES " + count + " ===");
            for (int index = 0; index < count; index++) {
                Address slot = base.add((long) index * 8L);
                long raw = currentProgram.getMemory().getLong(slot);
                Address target = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(raw);
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(target);
                Symbol symbol = currentProgram.getSymbolTable().getPrimarySymbol(target);
                String name = function != null
                    ? function.getName() + "@" + function.getEntryPoint()
                    : symbol != null ? symbol.getName(true) : "NO_SYMBOL";
                println(String.format("%02d %s -> %s %s", index, slot, target, name));
            }
        }
    }
}
