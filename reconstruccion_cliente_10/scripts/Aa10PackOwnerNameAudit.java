// Read-only r575 pack owner name packet provenance and serializer audit.
// @category AA10
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.HexFormat;

public class Aa10PackOwnerNameAudit extends GhidraScript {
    @Override
    public void run() throws Exception {
        String expected = "405242e05fff98bd337296355941c657445a65720902db1d2c905a0cff549734";
        String actual = currentProgram.getExecutableSHA256();
        println("Executable SHA256: " + actual);
        println("Image base: " + currentProgram.getImageBase());
        println("Language: " + currentProgram.getLanguageID());
        if (!expected.equalsIgnoreCase(actual) && !"2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76".equalsIgnoreCase(actual)) {
            throw new IllegalStateException("Unknown project; do not promote RVAs");
        }
        byte[] current = Files.readAllBytes(Path.of("E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575/Bin64/x2game.dll"));
        String currentHash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(current));
        if (!expected.equals(currentHash)) throw new IllegalStateException("Current DLL changed");
        println("Current DLL SHA256: " + currentHash);
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException(decompiler.getLastMessage());
            }
            for (String address : getScriptArgs()) {
                var function = currentProgram.getFunctionManager().getFunctionAt(toAddr(address));
                if (function == null) throw new IllegalStateException("Function not indexed: " + address);
                var ranges = function.getBody().getAddressRanges();
                while (ranges.hasNext()) {
                    var range = ranges.next();
                    int rva = (int)range.getMinAddress().subtract(currentProgram.getImageBase());
                    int length = (int)range.getLength();
                    int offset = fileOffset(current, rva, length);
                    byte[] original = new byte[length];
                    currentProgram.getMemory().getBytes(range.getMinAddress(), original);
                    if (!Arrays.equals(original, Arrays.copyOfRange(current, offset, offset + length))) {
                        throw new IllegalStateException("Function bytes differ at RVA " + Integer.toHexString(rva));
                    }
                    println("Exact code match RVA " + Integer.toHexString(rva) + " length " + length
                        + " SHA256 " + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original)));
                }
                var result = decompiler.decompileFunction(function, 45, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                for (String line : result.getDecompiledFunction().getC().split("\\R", -1)) println(line);
            }
        } finally {
            decompiler.dispose();
        }
    }

    private int fileOffset(byte[] image, int rva, int length) {
        ByteBuffer pe = ByteBuffer.wrap(image).order(ByteOrder.LITTLE_ENDIAN);
        int header = pe.getInt(0x3c);
        if (pe.getInt(header) != 0x4550) throw new IllegalStateException("Not PE");
        int sections = Short.toUnsignedInt(pe.getShort(header + 6));
        int table = header + 24 + Short.toUnsignedInt(pe.getShort(header + 20));
        for (int i = 0; i < sections; i++) {
            int at = table + i * 40;
            int va = pe.getInt(at + 12), size = pe.getInt(at + 16), raw = pe.getInt(at + 20);
            if (rva >= va && (long)rva + length <= (long)va + size) return raw + rva - va;
        }
        throw new IllegalStateException("RVA not backed by file data");
    }
}
