// Find functions that access several selected offsets of an in-memory structure.
// Usage: FindStructOffsetConsumers.java <minimum-distinct-offsets> <required-hex-offset> <hex-offset> [...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class FindStructOffsetConsumers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Expected minimum, required offset, and at least one search offset");
        }

        int minimum = Integer.parseInt(args[0]);
        String required = normalize(args[1]);
        List<String> offsets = new ArrayList<>();
        for (int index = 2; index < args.length; index++) {
            offsets.add(normalize(args[index]));
        }

        Map<Function, Set<String>> hits = new LinkedHashMap<>();
        Map<Function, List<String>> examples = new LinkedHashMap<>();
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            String rendered = instruction.toString().toLowerCase().replace(" ", "");
            if (rendered.contains("[rsp+") || rendered.contains("[rbp+")) {
                continue;
            }
            for (String offset : offsets) {
                if (!rendered.contains("+" + offset + "]")) {
                    continue;
                }
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(instruction.getAddress());
                if (function == null) {
                    break;
                }
                hits.computeIfAbsent(function, ignored -> new LinkedHashSet<>()).add(offset);
                List<String> functionExamples = examples.computeIfAbsent(
                    function, ignored -> new ArrayList<>());
                if (functionExamples.size() < 80) {
                    functionExamples.add(instruction.getAddress() + " " + instruction);
                }
                break;
            }
        }

        for (Map.Entry<Function, Set<String>> entry : hits.entrySet()) {
            if (entry.getValue().size() < minimum || !entry.getValue().contains(required)) {
                continue;
            }
            Function function = entry.getKey();
            println("=== STRUCT_CONSUMER " + function.getName() + " " +
                function.getEntryPoint() + " DISTINCT=" + entry.getValue().size() +
                " OFFSETS=" + String.join(",", entry.getValue()) + " ===");
            for (String example : examples.get(function)) {
                println(example);
            }
        }
    }

    private static String normalize(String value) {
        String normalized = value.toLowerCase();
        return normalized.startsWith("0x") ? normalized : "0x" + normalized;
    }
}
