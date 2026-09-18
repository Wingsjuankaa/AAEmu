// Read-only symbol/string index for the Battlerage plot condition investigation.
import ghidra.app.script.GhidraScript;

public class FindBattlerageConsumers extends GhidraScript {
    public void run() throws Exception {
        println("SHA256=" + currentProgram.getExecutableSHA256() + " BASE=" + currentProgram.getImageBase());
        var symbols = currentProgram.getSymbolTable().getAllSymbols(true);
        while (symbols.hasNext() && !monitor.isCancelled()) {
            var s = symbols.next();
            String name = s.getName(true);
            String lower = name.toLowerCase();
            if ((lower.contains("plot") && (lower.contains("condition") || lower.contains("visible")))
                    || lower.contains("plotobject") || lower.contains("resetcooldown") || lower.contains("skillcooldownreset"))
                println("SYMBOL " + s.getAddress() + " " + name);
        }
        var data = currentProgram.getListing().getDefinedData(true);
        while (data.hasNext() && !monitor.isCancelled()) {
            var item = data.next();
            if (!(item.getValue() instanceof String)) continue;
            String value = (String)item.getValue();
            String lower = value.toLowerCase();
            if ((lower.contains("plot") && (lower.contains("condition") || lower.contains("visible")))
                    || lower.contains("plotobject") || lower.contains("resetcooldown") || lower.contains("skillcooldownreset") || lower.equals("rstc")) {
                println("STRING " + item.getAddress() + " " + value);
                for (var ref : getReferencesTo(item.getAddress())) {
                    var f = getFunctionContaining(ref.getFromAddress());
                    println("REF " + ref.getFromAddress() + " " + (f == null ? "data" : f.getName() + "@" + f.getEntryPoint()));
                }
            }
        }
    }
}
