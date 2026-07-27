// Dump every defined string referenced by explicit AA8 functions.
// Usage: DumpAa8FunctionStrings.java <output> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class DumpAa8FunctionStrings extends GhidraScript {
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
            out.println("FORMAT\tAA8_FUNCTION_STRINGS_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
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
                Set<Address> seen = new HashSet<>();
                InstructionIterator instructions = currentProgram.getListing()
                    .getInstructions(function.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction instruction = instructions.next();
                    for (Reference reference :
                         instruction.getReferencesFrom()) {
                        Address target = reference.getToAddress();
                        if (!seen.add(target)) {
                            continue;
                        }
                        Data data = currentProgram.getListing()
                            .getDefinedDataAt(target);
                        if (data == null ||
                            !(data.getValue() instanceof String)) {
                            continue;
                        }
                        String value = String.valueOf(data.getValue())
                            .replace('\r', ' ')
                            .replace('\n', ' ');
                        out.println(
                            "STRING\t" + instruction.getAddress() + "\t" +
                            target + "\t" + value);
                    }
                }
                out.println("FUNCTION_END");
            }
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
