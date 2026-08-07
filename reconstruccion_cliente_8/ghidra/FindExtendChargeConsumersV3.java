// Locate functions consuming the 0x34-byte AA10 ExtendChargeEffectDesc.
//
// AA10 adds percent_damage_resource_type_id at +0x24 and moves the packed
// flags to +0x30.  Optimized x64 code aliases one descriptor pointer through
// several registers, so candidates are scored per function rather than per
// physical register.
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

public class FindExtendChargeConsumersV3 extends GhidraScript {
    private static final Pattern MEMORY = Pattern.compile(
        "\\[([A-Z][A-Z0-9]*) \\+ 0x([0-9A-Fa-f]+)\\]");
    private static final int[] SHIFTS = { 0, 4, 8, 0x10 };
    private static final int[] FIELDS = {
        0, 4, 8, 0xc, 0x10, 0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30
    };

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
            String upper = rendered.toUpperCase();
            String lower = rendered.toLowerCase();
            Matcher matcher = MEMORY.matcher(upper);
            while (matcher.find()) {
                String register = matcher.group(1);
                if (register.equals("RSP") || register.equals("RBP")) {
                    continue;
                }
                int offset = Integer.parseInt(matcher.group(2), 16);
                String key = function.getEntryPoint().toString();
                functions.put(key, function);
                fields.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                if (upper.startsWith("MOVSS") || upper.startsWith("MULSS") ||
                    upper.startsWith("ADDSS") || upper.startsWith("SUBSS") ||
                    upper.startsWith("CVTSI2SS")) {
                    floatAccesses.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                }
                if (lower.contains("byte ptr")) {
                    byteAccesses.computeIfAbsent(key, ignored -> new LinkedHashSet<>()).add(offset);
                }
                List<String> lines = examples.computeIfAbsent(key, ignored -> new ArrayList<>());
                if (lines.size() < 180) {
                    lines.add(instruction.getAddress() + " " + rendered);
                }
            }
        }

        int candidates = 0;
        for (Map.Entry<String, Set<Integer>> entry : fields.entrySet()) {
            String key = entry.getKey();
            Set<Integer> floatHits = floatAccesses.getOrDefault(key, Set.of());
            Set<Integer> byteHits = byteAccesses.getOrDefault(key, Set.of());
            for (int shift : SHIFTS) {
                int shapeHits = 0;
                for (int field : FIELDS) {
                    if (entry.getValue().contains(shift + field)) {
                        shapeHits++;
                    }
                }
                int floatCount = 0;
                for (int field : new int[] { 8, 0xc, 0x18 }) {
                    if (floatHits.contains(shift + field)) {
                        floatCount++;
                    }
                }
                boolean hasFlags = byteHits.contains(shift + 0x30) ||
                    entry.getValue().contains(shift + 0x30);
                if (shapeHits < 2 || !hasFlags) {
                    continue;
                }
                Function function = functions.get(key);
                println("=== EXTEND_CHARGE_V3 " + function.getName() + " " +
                    function.getEntryPoint() + " KEY=" + key +
                    " SHIFT=0x" + Integer.toHexString(shift) +
                    " SHAPE_HITS=" + shapeHits +
                    " FLOAT_HITS=" + floatCount +
                    " FLAG_BYTE=" + byteHits.contains(shift + 0x30) + " ===");
                for (String line : examples.get(key)) {
                    println(line);
                }
                candidates++;
            }
        }
        println("=== EXTEND_CHARGE_V3_CANDIDATES " + candidates + " ===");
    }
}
