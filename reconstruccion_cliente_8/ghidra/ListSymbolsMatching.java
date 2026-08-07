// List symbols and functions whose names contain one of the supplied fragments.
// Usage: ListSymbolsMatching.java <fragment> [<fragment> ...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class ListSymbolsMatching extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected at least one name fragment");
        }

        for (String rawFragment : args) {
            String fragment = rawFragment.toLowerCase();
            println("=== SYMBOLS_MATCHING " + rawFragment + " ===");
            int count = 0;
            SymbolIterator symbols = currentProgram.getSymbolTable().getAllSymbols(true);
            while (symbols.hasNext() && !monitor.isCancelled()) {
                Symbol symbol = symbols.next();
                if (!symbol.getName(true).toLowerCase().contains(fragment)) {
                    continue;
                }
                println(symbol.getAddress() + " " + symbol.getSymbolType() + " " +
                    symbol.getName(true));
                count++;
            }

            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                if (!function.getName(true).toLowerCase().contains(fragment)) {
                    continue;
                }
                println(function.getEntryPoint() + " FUNCTION " + function.getName(true));
                count++;
            }
            println("=== MATCH_COUNT " + count + " ===");
        }
    }
}
