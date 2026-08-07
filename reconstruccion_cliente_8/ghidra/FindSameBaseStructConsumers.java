// Find functions that access several selected offsets through the same register.
// Usage: FindSameBaseStructConsumers.java <minimum-distinct-offsets> <required-hex-offset> <hex-offset> [...]
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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class FindSameBaseStructConsumers extends GhidraScript {
    private static final Pattern MEMORY = Pattern.compile(
        "\\[([A-Z][A-Z0-9]*) \\+ 0x([0-9A-Fa-f]+)\\]");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Expected minimum, required offset, and at least one search offset");
        }

        int minimum = Integer.parseInt(args[0]);
        String required = normalize(args[1]);
        Set<String> wanted = new LinkedHashSet<>();
        for (int index = 2; index < args.length; index++) {
            wanted.add(normalize(args[index]));
        }

        Map<String, Set<String>> hits = new LinkedHashMap<>();
        Map<String, List<String>> examples = new LinkedHashMap<>();
        Map<String, Function> functions = new LinkedHashMap<>();
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            if (function == null) {
                continue;
            }

            Matcher matcher = MEMORY.matcher(instruction.toString());
            while (matcher.find()) {
                String register = matcher.group(1).toUpperCase();
                if (register.equals("RSP") || register.equals("RBP")) {
                    continue;
                }
                String offset = normalize(matcher.group(2));
                if (!wanted.contains(offset)) {
                    continue;
                }
                String key = function.getEntryPoint() + ":" + register;
                functions.put(key, function);
                hits.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                List<String> lines = examples.computeIfAbsent(key, ignored -> new ArrayList<>());
                if (lines.size() < 60) {
                    lines.add(instruction.getAddress() + " " + instruction);
                }
            }
        }

        for (Map.Entry<String, Set<String>> entry : hits.entrySet()) {
            if (entry.getValue().size() < minimum || !entry.getValue().contains(required)) {
                continue;
            }
            Function function = functions.get(entry.getKey());
            println("=== SAME_BASE_STRUCT_CONSUMER " + function.getName() + " " +
                function.getEntryPoint() + " KEY=" + entry.getKey() +
                " DISTINCT=" + entry.getValue().size() +
                " OFFSETS=" + String.join(",", entry.getValue()) + " ===");
            for (String line : examples.get(entry.getKey())) {
                println(line);
            }
        }
    }

    private static String normalize(String value) {
        String normalized = value.toLowerCase();
        if (normalized.startsWith("0x")) {
            normalized = normalized.substring(2);
        }
        normalized = normalized.replaceFirst("^0+(?!$)", "");
        return "0x" + normalized;
    }
}
