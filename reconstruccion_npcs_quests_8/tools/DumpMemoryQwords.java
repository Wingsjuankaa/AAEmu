// Dumps raw qwords and resolved symbols for a small Ghidra address range.

import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Symbol;

public class DumpMemoryQwords extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) {
            throw new IllegalArgumentException(
                "usage: DumpMemoryQwords <address> <count> <output-file>");
        }

        Address address = toAddr(args[0]);
        int count = Integer.decode(args[1]);
        try (PrintWriter writer = new PrintWriter(new File(args[2]), "UTF-8")) {
            for (int index = 0; index < count; index++) {
                Address current = address.add(index * 8L);
                long value = getLong(current);
                Address target = toAddr(value);
                Symbol symbol = getSymbolAt(target);
                writer.printf(
                    "%s = %016x -> %s%n",
                    current,
                    value,
                    symbol == null ? "" : symbol.getName());
            }
        }
    }
}
