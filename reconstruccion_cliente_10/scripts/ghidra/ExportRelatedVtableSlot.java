// Read-only: locate data references to a known method and export another slot.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import java.util.HashSet;

public class ExportRelatedVtableSlot extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) throw new IllegalArgumentException("method sourceOffset targetOffset (hex)");
        long delta = Long.parseLong(args[2],16) - Long.parseLong(args[1],16);
        println("SHA256=" + currentProgram.getExecutableSHA256() + " BASE=" + currentProgram.getImageBase());
        var seen = new HashSet<String>();
        var decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (var ref : getReferencesTo(toAddr(args[0]))) {
                var at = ref.getFromAddress();
                if (getFunctionContaining(at) != null) continue;
                var target = at.add(delta);
                var function = getFunctionAt(toAddr(getLong(target)));
                println("REFERENCE=" + at + " TARGET_SLOT=" + target + " FUNCTION=" + function);
                if (function == null || !seen.add(function.getEntryPoint().toString())) continue;
                var result = decompiler.decompileFunction(function,90,monitor);
                if (result.decompileCompleted()) println(result.getDecompiledFunction().getC());
            }
        } finally { decompiler.dispose(); }
    }
}
