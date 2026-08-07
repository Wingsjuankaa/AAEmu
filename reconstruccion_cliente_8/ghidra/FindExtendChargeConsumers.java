// Locate functions consuming the 0x34-byte ExtendChargeEffectDesc shape.
// The descriptor has packed flags at +0x30 and float fields at +0x08,+0x0c,+0x18.
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

public class FindExtendChargeConsumers extends GhidraScript {
    private static final Pattern MEMORY = Pattern.compile(
        "\\[([A-Z][A-Z0-9]*) \\+ 0x([0-9A-Fa-f]+)\\]");
    private static final int[] SHIFTS = { 0, 4, 8, 0x10 };

    @Override
    public void run() throws Exception {
        Map<String, Set<Integer>> fields = new LinkedHashMap<>();
        Map<String, Set<Integer>> floatAccesses = new LinkedHashMap<>();
        Map<String, Set<Integer>> byteAccesses = new LinkedHashMap<>();
        Map<String, Function> functions = new LinkedHashMap<>();
        Map<String, List<String>> examples = new LinkedHashMap<>();

        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            if (function == null) {
                continue;
            }
            String rendered = instruction.toString();
            Matcher matcher = MEMORY.matcher(rendered);
            while (matcher.find()) {
                String register = matcher.group(1).toUpperCase();
                if (register.equals("RSP") || register.equals("RBP")) {
                    continue;
                }
                int offset = Integer.parseInt(matcher.group(2), 16);
                String key = function.getEntryPoint() + ":" + register;
                functions.put(key, function);
                fields.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                if (rendered.startsWith("MOVSS") || rendered.startsWith("MULSS") ||
                    rendered.startsWith("ADDSS") || rendered.startsWith("SUBSS")) {
                    floatAccesses.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                }
                if (rendered.contains("byte ptr")) {
                    byteAccesses.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                }
                List<String> lines = examples.computeIfAbsent(key, ignored -> new ArrayList<>());
                if (lines.size() < 100) {
                    lines.add(instruction.getAddress() + " " + rendered);
                }
            }
        }

        for (Map.Entry<String, Set<Integer>> entry : fields.entrySet()) {
            String key = entry.getKey();
            Set<Integer> floatHits = floatAccesses.getOrDefault(key, Set.of());
            Set<Integer> byteHits = byteAccesses.getOrDefault(key, Set.of());
            for (int shift : SHIFTS) {
                int[] shape = {
                    shift + 8, shift + 0xc, shift + 0x10, shift + 0x14,
                    shift + 0x18, shift + 0x1c, shift + 0x20, shift + 0x24,
                    shift + 0x28, shift + 0x2c, shift + 0x30
                };
                int shapeHits = 0;
                for (int offset : shape) {
                    if (entry.getValue().contains(offset)) {
                        shapeHits++;
                    }
                }
                boolean hasFloat = floatHits.contains(shift + 8) ||
                    floatHits.contains(shift + 0xc) || floatHits.contains(shift + 0x18);
                if (shapeHits < 5 || !hasFloat || !byteHits.contains(shift + 0x30)) {
                    continue;
                }
                Function function = functions.get(key);
                println("=== EXTEND_CHARGE_CONSUMER " + function.getName() + " " +
                    function.getEntryPoint() + " KEY=" + key +
                    " SHIFT=0x" + Integer.toHexString(shift) +
                    " SHAPE_HITS=" + shapeHits + " ===");
                for (String line : examples.get(key)) {
                    println(line);
                }
            }
        }
    }

}
