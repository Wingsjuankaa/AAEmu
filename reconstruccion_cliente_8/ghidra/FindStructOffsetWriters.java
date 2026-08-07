// Find functions that write several selected offsets of an in-memory structure.
// Usage: FindStructOffsetWriters.java <minimum-distinct-offsets> <hex-offset> [...]
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

public class FindStructOffsetWriters extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected minimum-distinct-offsets and at least one hex offset");
        }

        int minimum = Integer.parseInt(args[0]);
        List<String> needles = new ArrayList<>();
        for (int index = 1; index < args.length; index++) {
            String value = args[index].toLowerCase();
            if (!value.startsWith("0x")) {
                value = "0x" + value;
            }
            needles.add("+" + value + "]");
        }

        Map<Function, Set<String>> hits = new LinkedHashMap<>();
        Map<Function, List<String>> examples = new LinkedHashMap<>();
        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            String mnemonic = instruction.getMnemonicString().toLowerCase();
            if (!mnemonic.startsWith("mov") || instruction.getNumOperands() == 0) {
                continue;
            }
            String destination = instruction.getDefaultOperandRepresentation(0)
                .toLowerCase().replace(" ", "");
            if (!destination.contains("[")) {
                continue;
            }
            for (String needle : needles) {
                if (!destination.contains(needle)) {
                    continue;
                }
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(instruction.getAddress());
                if (function == null) {
                    break;
                }
                hits.computeIfAbsent(function, ignored -> new LinkedHashSet<>())
                    .add(needle.substring(1, needle.length() - 1));
                List<String> functionExamples = examples.computeIfAbsent(
                    function, ignored -> new ArrayList<>());
                if (functionExamples.size() < 64) {
                    functionExamples.add(instruction.getAddress() + " " + instruction);
                }
                break;
            }
        }

        for (Map.Entry<Function, Set<String>> entry : hits.entrySet()) {
            if (entry.getValue().size() < minimum) {
                continue;
            }
            Function function = entry.getKey();
            println("=== STRUCT_WRITER " + function.getName() + " " +
                function.getEntryPoint() + " DISTINCT=" + entry.getValue().size() +
                " OFFSETS=" + String.join(",", entry.getValue()) + " ===");
            for (String example : examples.get(function)) {
                println(example);
            }
        }
    }
}
