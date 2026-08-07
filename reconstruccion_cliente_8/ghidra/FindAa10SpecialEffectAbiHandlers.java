// Locate functions that consume SpecialEffectDesc through the known x64 ABI.
// A SkillResult return uses hidden RCX; SpecialEffectDesc const* is therefore
// received in RDX.  This script follows only direct MOV aliases of RDX and
// invalidates aliases when overwritten, avoiding the broad offset-only false
// positives produced by generic structure scanners.
// An optional fifth argument restricts results to functions that directly call
// the supplied address. This is useful for SkillUse because every real handler
// must resolve value1 through SkillManager::GetSkillTemplate (FUN_39abf2c0).
// Usage: FindAa10SpecialEffectAbiHandlers.java [minimum-fields] [instruction-limit]
//        [range-start] [range-end] [required-direct-callee]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.address.Address;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public class FindAa10SpecialEffectAbiHandlers extends GhidraScript {
    private static final List<String> OFFSETS = Arrays.asList(
        "0x4", "0x8", "0xc", "0x10", "0x14", "0x18", "0x1c");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int minimum = args.length > 0 ? Integer.parseInt(args[0]) : 3;
        int limit = args.length > 1 ? Integer.parseInt(args[1]) : 120;
        long rangeStart = args.length > 2 ? Long.parseUnsignedLong(args[2], 16) : 0x39000000L;
        long rangeEnd = args.length > 3 ? Long.parseUnsignedLong(args[3], 16) : 0x39e00000L;
        Long requiredCallee = args.length > 4
            ? Long.parseUnsignedLong(args[4], 16)
            : null;
        int count = 0;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            long entry = function.getEntryPoint().getOffset();
            if (entry < rangeStart || entry >= rangeEnd) {
                continue;
            }

            Set<String> aliases = new LinkedHashSet<>();
            aliases.add("rdx");
            Set<String> fields = new LinkedHashSet<>();
            List<String> examples = new ArrayList<>();
            int calls = 0;
            boolean callsRequired = requiredCallee == null;
            int seen = 0;

            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext() && seen++ < limit) {
                Instruction instruction = instructions.next();
                String mnemonic = instruction.getMnemonicString().toLowerCase();
                String rendered = instruction.toString().toLowerCase().replace(" ", "");
                if (mnemonic.startsWith("call")) {
                    calls++;
                    for (Address flow : instruction.getFlows()) {
                        if (requiredCallee != null &&
                            flow.getOffset() == requiredCallee.longValue()) {
                            callsRequired = true;
                        }
                    }
                }

                int comma = rendered.indexOf(',');
                String destination = comma < 0 ? "" : rendered.substring(
                    mnemonic.length(), comma);
                String source = comma < 0 ? "" : rendered.substring(comma + 1);

                // Record reads only. A memory destination is a write and does
                // not demonstrate that the descriptor field was consumed.
                if (!destination.contains("[")) {
                    for (String alias : aliases) {
                        for (String offset : OFFSETS) {
                            if (source.contains("[" + alias + "+" + offset + "]")) {
                                fields.add(offset);
                                if (examples.size() < 20) {
                                    examples.add(instruction.getAddress() + " " + instruction);
                                }
                            }
                        }
                    }
                }

                if (mnemonic.equals("mov") || mnemonic.equals("lea")) {
                    String dest64 = normalizeRegister(destination);
                    if (!dest64.isEmpty()) {
                        boolean derivesFromDescriptor = false;
                        for (String alias : aliases) {
                            if (source.equals(alias) || source.equals("[" + alias + "]")) {
                                derivesFromDescriptor = true;
                                break;
                            }
                        }
                        if (derivesFromDescriptor) {
                            aliases.add(dest64);
                        }
                        else if (!dest64.equals("rdx")) {
                            aliases.remove(dest64);
                        }
                    }
                }
            }

            // SkillUse necessarily consumes value1/value2/value3. Restrict the
            // output to that exact descriptor prefix; generic qword/vector
            // structures overwhelmingly match 8/10/18 instead.
            if (fields.size() < minimum || calls == 0 || !callsRequired ||
                !fields.contains("0x4") || !fields.contains("0x8") ||
                !fields.contains("0xc")) {
                continue;
            }
            println("=== AA10_SPECIAL_ABI_HANDLER " + function.getName() + " " +
                function.getEntryPoint() + " FIELDS=" + String.join(",", fields) +
                " CALLS=" + calls + " ===");
            for (String example : examples) {
                println(example);
            }
            count++;
        }
        println("=== CANDIDATE_COUNT " + count + " ===");
    }

    private static String normalizeRegister(String raw) {
        String value = raw.replace("qwordptr", "").replace("dwordptr", "")
            .replace("wordptr", "").replace("byteptr", "");
        if (value.matches("r(8|9|10|11|12|13|14|15|ax|bx|cx|dx|si|di|bp)")) {
            return value;
        }
        if (value.matches("e(ax|bx|cx|dx|si|di|bp)")) {
            return "r" + value.substring(1);
        }
        return "";
    }
}
