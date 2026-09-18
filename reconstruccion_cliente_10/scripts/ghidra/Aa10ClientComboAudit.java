// Read-only r575 SkillComboMan and combat_sync closure. No analysis or mutation.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;

public class Aa10ClientComboAudit extends GhidraScript {
    public void run() throws Exception {
        String sha = "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76";
        if (!sha.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !currentProgram.getImageBase().equals(toAddr("39000000")))
            throw new IllegalStateException("Expected the immutable r575 x64 release x2game.dll");
        println("SHA256=" + sha + " BASE=" + currentProgram.getImageBase());
        String[] addresses = {"396e4520", "396e4640", "396e4760", "396df870",
            "396611c0", "392444d0", "392f8210", "39b98da0", "39b99c70"};
        var decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (String address : addresses) {
                var function = getFunctionAt(toAddr(address));
                if (function == null) throw new IllegalStateException(address);
                println("FUNCTION=" + function.getEntryPoint());
                var result = decompiler.decompileFunction(function, 120, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                println(result.getDecompiledFunction().getC());
            }
        } finally { decompiler.dispose(); }
    }
}
