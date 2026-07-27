// Dump the complete instruction listing for explicit AA8 function addresses.
// Usage: DumpAa8Instructions.java <output> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class DumpAa8Instructions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output file and at least one function address");
        }
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM\t" + currentProgram.getName());
            for (int index = 1; index < args.length; index++) {
                Address requested = toAddr(args[index]);
                Function function = currentProgram.getListing()
                    .getFunctionContaining(requested);
                if (function == null) {
                    out.println("NO_FUNCTION\t" + requested);
                    continue;
                }
                out.println(
                    "FUNCTION_BEGIN\t" + function.getName() + "\t" +
                    function.getEntryPoint());
                InstructionIterator instructions = currentProgram.getListing()
                    .getInstructions(function.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction instruction = instructions.next();
                    out.println(
                        instruction.getAddress() + "\t" +
                        instruction.toString());
                }
                out.println("FUNCTION_END");
            }
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
