// Read-only Ghidra helper: decompile an address and every function that references it.
// Usage: -postScript DecompileAddressAndXrefs.java 39ab79d0
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.util.LinkedHashSet;
import java.util.Set;

public class DecompileAddressAndXrefs extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            printerr("Expected one hexadecimal address");
            return;
        }

        Address target = toAddr(args[0]);
        Set<Function> functions = new LinkedHashSet<>();
        Function targetFunction = getFunctionContaining(target);
        if (targetFunction != null) {
            functions.add(targetFunction);
        }

        for (Reference reference : getReferencesTo(target)) {
            Function caller = getFunctionContaining(reference.getFromAddress());
            if (caller != null) {
                functions.add(caller);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (Function function : functions) {
                println("FUNCTION " + function.getName() + " @ " + function.getEntryPoint());
                DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
                if (result.decompileCompleted()) {
                    println(result.getDecompiledFunction().getC());
                } else {
                    printerr("Failed to decompile " + function.getName() + ": " + result.getErrorMessage());
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
