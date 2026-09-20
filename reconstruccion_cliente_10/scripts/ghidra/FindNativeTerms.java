// Read-only symbol/string references for an explicit native frontier.
import ghidra.app.script.GhidraScript;
import java.util.Locale;

public class FindNativeTerms extends GhidraScript {
    private boolean matches(String value) {
        String lower = value.toLowerCase(Locale.ROOT);
        for (String term : getScriptArgs())
            if (lower.contains(term.toLowerCase(Locale.ROOT))) return true;
        return false;
    }

    public void run() throws Exception {
        if (getScriptArgs().length == 0) throw new IllegalArgumentException("Supply search terms");
        println("SHA256=" + currentProgram.getExecutableSHA256() + " BASE=" + currentProgram.getImageBase());
        var symbols = currentProgram.getSymbolTable().getAllSymbols(true);
        while (symbols.hasNext() && !monitor.isCancelled()) {
            var symbol = symbols.next();
            if (matches(symbol.getName(true)))
                println("SYMBOL " + symbol.getAddress() + " " + symbol.getName(true));
        }
        var entries = currentProgram.getListing().getDefinedData(true);
        while (entries.hasNext() && !monitor.isCancelled()) {
            var entry = entries.next();
            if (!(entry.getValue() instanceof String text) || !matches(text)) continue;
            println("STRING " + entry.getAddress() + " " + text);
            for (var ref : getReferencesTo(entry.getAddress())) {
                var function = getFunctionContaining(ref.getFromAddress());
                println("REF " + ref.getFromAddress() + " " +
                    (function == null ? "data" : function.getName() + "@" + function.getEntryPoint()));
            }
        }
    }
}
