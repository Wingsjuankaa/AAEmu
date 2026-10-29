// Read-only discovery of Escape and MoveToRezPoint consumers in the r575 Zone DLL.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.symbol.Reference;

public class Aa10ZoneEscapeStringRefs extends GhidraScript {
    public void run() throws Exception {
        String sha = "8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a";
        if (!sha.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !currentProgram.getImageBase().equals(toAddr("39000000")))
            throw new IllegalStateException("Expected immutable r575 x64 Zone DLL");
        println("SHA256=" + sha);
        var iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (value == null) continue;
            String label = value.toString();
            String lower = label.toLowerCase();
            if (!lower.contains("escape") && !lower.contains("movetorezpoint")) continue;
            println("STRING " + data.getAddress() + " " + label);
            for (Reference ref : currentProgram.getReferenceManager().getReferencesTo(data.getAddress())) {
                var function = getFunctionContaining(ref.getFromAddress());
                println("REF " + ref.getFromAddress() + " FUNCTION " +
                    (function == null ? "?" : function.getEntryPoint() + " " + function.getName()));
            }
        }
    }
}
