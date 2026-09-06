// Read-only extraction of exact World Level functions and their raw bytes.
// Usage: Aa10WorldLevelNativeAudit.java <output-directory> <VA> [...]
// @category AA10
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;

public class Aa10WorldLevelNativeAudit extends GhidraScript {
    @Override public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) throw new IllegalArgumentException("output-directory and VAs required");
        Path output = Path.of(args[0]);
        Files.createDirectories(output);
        String identity = "program=" + currentProgram.getName() + "\nsha256=" +
            currentProgram.getExecutableSHA256() + "\nbase=" + currentProgram.getImageBase() +
            "\nlanguage=" + currentProgram.getLanguageID() + "\n";
        Files.writeString(output.resolve("identity.txt"), identity);
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException(decompiler.getLastMessage());
        try {
            for (int i = 1; i < args.length; i++) {
                Address address = toAddr(args[i]);
                Function function = getFunctionContaining(address);
                if (function == null) throw new IllegalStateException("No function at " + address);
                var result = decompiler.decompileFunction(function, 60, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                String name = function.getEntryPoint().toString();
                Files.writeString(output.resolve(name + ".c"), result.getDecompiledFunction().getC());
                StringBuilder ranges = new StringBuilder();
                for (var range : function.getBody().getAddressRanges()) {
                    byte[] bytes = new byte[(int)range.getLength()];
                    currentProgram.getMemory().getBytes(range.getMinAddress(), bytes);
                    ranges.append(range.getMinAddress().subtract(currentProgram.getImageBase()))
                        .append(" ").append(HexFormat.of().formatHex(bytes)).append("\n");
                }
                Files.writeString(output.resolve(name + ".bytes"), ranges);
                StringBuilder refs = new StringBuilder();
                for (var ref : getReferencesTo(function.getEntryPoint())) {
                    Function caller = getFunctionContaining(ref.getFromAddress());
                    refs.append(ref.getFromAddress()).append(" ").append(ref.getReferenceType())
                        .append(" ").append(caller == null ? "NO_FUNCTION" : caller.getEntryPoint()).append("\n");
                }
                Files.writeString(output.resolve(name + ".refs"), refs);
                println("Extracted " + name + " " + function.getBody().getNumAddresses() + " bytes");
            }
        } finally { decompiler.dispose(); }
    }
}
