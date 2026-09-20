// Read-only r575 SkillStarted -> pending-request removal -> failure/success dispatch.
// Run with -readOnly -noanalysis against AA10X2GameRelease/x2game.dll.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;

public class Aa10SkillStartedResultAudit extends GhidraScript {
    public void run() throws Exception {
        String sha = "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76";
        if (!sha.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !currentProgram.getImageBase().equals(toAddr("39000000")))
            throw new IllegalStateException("Expected immutable r575 x64 release x2game.dll");
        println("SHA256=" + sha + " BASE=" + currentProgram.getImageBase());
        String[] addresses = {"39ac68c0", "3933bcd0", "396dee00", "396d5290", "396d6240"};
        var decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (String address : addresses) {
                var function = getFunctionAt(toAddr(address));
                if (function == null) throw new IllegalStateException(address);
                println("FUNCTION=" + function.getEntryPoint() + " END=" + function.getBody().getMaxAddress());
                var result = decompiler.decompileFunction(function, 120, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                println(result.getDecompiledFunction().getC());
            }
        } finally { decompiler.dispose(); }
    }
}
