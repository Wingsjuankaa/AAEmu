// Find functions that mention one special-effect type and read several fields
// from a 32-byte descriptor-shaped object.  Intended to locate the retail
// switch/dispatcher when no symbolic name survives.
// Usage: FindSpecialTypeDispatch.java <type-hex> [minimum-read-fields]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class FindSpecialTypeDispatch extends GhidraScript {
    private static final List<String> OFFSETS = Arrays.asList(
        "0x4", "0x8", "0xc", "0x10", "0x14", "0x18", "0x1c");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected special effect type in hex");
        }
        String wanted = args[0].toLowerCase();
        if (!wanted.startsWith("0x")) {
            wanted = "0x" + wanted;
        }
        int minimum = args.length > 1 ? Integer.parseInt(args[1]) : 4;
        int count = 0;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            boolean mentionsType = false;
            Set<String> reads = new LinkedHashSet<>();
            List<String> examples = new ArrayList<>();
            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (iterator.hasNext()) {
                Instruction instruction = iterator.next();
                String text = instruction.toString().toLowerCase().replace(" ", "");
                if (text.endsWith("," + wanted) || text.contains("," + wanted + ",")) {
                    mentionsType = true;
                    if (examples.size() < 30) {
                        examples.add(instruction.getAddress() + " " + instruction);
                    }
                }
                int comma = text.indexOf(',');
                String destination = comma < 0 ? text : text.substring(0, comma);
                for (String offset : OFFSETS) {
                    if (!text.contains("+" + offset + "]")) {
                        continue;
                    }
                    // Ignore obvious writes whose first operand is the memory field.
                    if (destination.contains("+" + offset + "]")) {
                        continue;
                    }
                    reads.add(offset);
                    if (examples.size() < 30) {
                        examples.add(instruction.getAddress() + " " + instruction);
                    }
                }
            }
            if (!mentionsType || reads.size() < minimum) {
                continue;
            }
            println("=== SPECIAL_TYPE_DISPATCH_CANDIDATE " + function.getName() + " " +
                function.getEntryPoint() + " TYPE=" + wanted + " READS=" +
                String.join(",", reads) + " ===");
            for (String example : examples) {
                println(example);
            }
            count++;
        }
        println("=== CANDIDATE_COUNT " + count + " ===");
    }
}
