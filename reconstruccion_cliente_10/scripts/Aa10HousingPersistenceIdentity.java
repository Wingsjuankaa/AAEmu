// Read-only identity gate for the Zone housing persistence investigation.
// @category AA10
import ghidra.app.script.GhidraScript;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

public class Aa10HousingPersistenceIdentity extends GhidraScript {
    @Override public void run() throws Exception {
        String expected = "8936ce897d7610d2d4e0a27be9cc97708930c33e4cb910c03d17f23088a4891a";
        Path path = Path.of("E:/AAEmu/rama_10/client/ArcheAge-Returns-10.0.2.13-r575/Bin64/x2game-dev_dedicate.dll");
        String actual = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
        println("Project SHA256=" + currentProgram.getExecutableSHA256());
        println("Operational SHA256=" + actual);
        println("Image base=" + currentProgram.getImageBase() + " language=" + currentProgram.getLanguageID());
        if (!expected.equals(actual) || !expected.equalsIgnoreCase(currentProgram.getExecutableSHA256())) {
            throw new IllegalStateException("Identity mismatch; native addresses must not be promoted");
        }
        println("Identity confirmed; loader evidence does not prove World/DB persistence policy.");
    }
}
