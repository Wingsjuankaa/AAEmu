// Read-only discovery of r575 skill requirement table consumers.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.symbol.Reference;

public class Aa10SkillReqStringRefs extends GhidraScript {
    public void run() throws Exception {
        String sha = "2735819f39646ea07af002babc1ec105d091c4821e7b1290cb8525e809719f76";
        if (!sha.equalsIgnoreCase(currentProgram.getExecutableSHA256()) ||
            !currentProgram.getImageBase().equals(toAddr("39000000")))
            throw new IllegalStateException("Expected immutable r575 x64 release x2game.dll");
        println("SHA256=" + sha + " BASE=" + currentProgram.getImageBase());
        var iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (value == null) continue;
            String label = value.toString();
            if (!label.contains("skill_reqs") && !label.contains("skill_req_skills") &&
                !label.contains("SkillReq")) continue;
            println("STRING " + data.getAddress() + " " + label);
            for (Reference ref : currentProgram.getReferenceManager().getReferencesTo(data.getAddress())) {
                var function = getFunctionContaining(ref.getFromAddress());
                println("REF " + ref.getFromAddress() + " FUNCTION " +
                    (function == null ? "?" : function.getEntryPoint() + " " + function.getName()));
            }
        }
    }
}
