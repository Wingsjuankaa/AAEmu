// Decompile selected virtual addresses from the current program.
// Usage: DecompileSelectedFunctions.java <timeout-seconds> <address> [<address> ...]
// @category AA8

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DecompileSelectedFunctions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected timeout-seconds and at least one virtual address");
        }

        int timeoutSeconds = Integer.parseInt(args[0]);
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.setSimplificationStyle("decompile");
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException(
                "Decompiler refused program: " + decompiler.getLastMessage());
        }

        try {
            for (int index = 1; index < args.length; index++) {
                Address address = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(args[index]);
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(address);
                if (function == null) {
                    println("=== NO_FUNCTION " + address + " ===");
                    continue;
                }

                println("=== FUNCTION " + function.getName() + " " +
                    function.getEntryPoint() + " ===");
                DecompileResults result = decompiler.decompileFunction(
                    function, timeoutSeconds, monitor);
                if (!result.decompileCompleted()) {
                    println("=== DECOMPILE_FAILED " + result.getErrorMessage() + " ===");
                    continue;
                }
                println(result.getDecompiledFunction().getC());
                println("=== END_FUNCTION ===");
            }
        }
        finally {
            decompiler.dispose();
        }
    }
}
