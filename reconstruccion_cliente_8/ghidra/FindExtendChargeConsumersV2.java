// Locate functions consuming the native 0x30-byte ExtendChargeEffectDesc.
//
// LoadExtendChargeEffectDescs copies 0x30 bytes after the row id.  The packed
// boolean flags therefore live at +0x2c (not +0x30):
//   +00 charge_buff_id       +04 damage_type_id
//   +08 dps_inc_multiplier   +0c dps_multiplier
//   +10 fixed_max            +14 fixed_min
//   +18 level_md             +1c level_va_end
//   +20 level_va_start       +24 percent_max
//   +28 percent_min          +2c packed flags
// Usage: FindExtendChargeConsumersV2.java
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

public class FindExtendChargeConsumersV2 extends GhidraScript {
    private static final Pattern MEMORY = Pattern.compile(
        "\\[([A-Z][A-Z0-9]*) \\+ 0x([0-9A-Fa-f]+)\\]");
    private static final int[] SHIFTS = { 0, 4, 8, 0x10 };
    private static final int[] FIELDS = {
        0, 4, 8, 0xc, 0x10, 0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c
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
                // Score by function, not by a single physical register.  The
                // optimized x64 builds freely alias one descriptor pointer
                // through RCX/RDX/R8/R9 and callee-saved registers.
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
                if (lines.size() < 160) {
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
                boolean hasFlags = byteHits.contains(shift + 0x2c) ||
                    entry.getValue().contains(shift + 0x2c);
                // Optimized builds commonly copy the descriptor pointer into
                // several registers before consuming it.  Keep partial shapes
                // visible when they still touch the packed flag byte; the
                // decompiler/call graph is used to join those aliases later.
                if (shapeHits < 2 || !hasFlags) {
                    continue;
                }
                Function function = functions.get(key);
                println("=== EXTEND_CHARGE_V2 " + function.getName() + " " +
                    function.getEntryPoint() + " KEY=" + key +
                    " SHIFT=0x" + Integer.toHexString(shift) +
                    " SHAPE_HITS=" + shapeHits +
                    " FLOAT_HITS=" + floatCount +
                    " FLAG_BYTE=" + byteHits.contains(shift + 0x2c) + " ===");
                for (String line : examples.get(key)) {
                    println(line);
                }
                candidates++;
            }
        }
        println("=== EXTEND_CHARGE_V2_CANDIDATES " + candidates + " ===");
    }
}
