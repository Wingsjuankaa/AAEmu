// Read-only r575 audit of functions referencing the skill-requirement storage offset.
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.script.GhidraScript;

public class Aa10SkillReqEvalAudit extends GhidraScript {
    public void run() throws Exception {
        String sha = "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76";
        if (!sha.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !currentProgram.getImageBase().equals(toAddr("39000000")))
            throw new IllegalStateException("Expected immutable r575 x64 release x2game.dll");
        var decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (String address : new String[] {
                "393c41f0", "395270b0", "39528770", "39a2aac0", "39a76be0"
            }) {
                var function = getFunctionAt(toAddr(address));
                println("FUNCTION " + address + " " + (function == null ? "missing" : function.getName()));
                if (function == null) continue;
                var result = decompiler.decompileFunction(function, 120, monitor);
                println(result.decompileCompleted() ? result.getDecompiledFunction().getC()
                    : "ERROR " + result.getErrorMessage());
            }
        } finally {
            decompiler.dispose();
        }
    }
}
