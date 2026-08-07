// Find x64 functions that consume the polymorphic effect wrapper layout:
// kind at +4 and descriptor pointer at +8 from the same base register.
// Usage: FindEffectWrapperDispatchers.java [min-address] [max-address]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class FindEffectWrapperDispatchers extends GhidraScript {
    private static final Pattern FIELD = Pattern.compile(
        "\\[([re][a-z0-9]{2})(?:\\+0x(4|8))\\]");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        long minimum = args.length > 0 ? Long.parseUnsignedLong(args[0], 16) : 0;
        long maximum = args.length > 1
            ? Long.parseUnsignedLong(args[1], 16)
            : Long.MAX_VALUE;
        int count = 0;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            long entry = function.getEntryPoint().getOffset();
            if (Long.compareUnsigned(entry, minimum) < 0 ||
                Long.compareUnsigned(entry, maximum) >= 0) {
                continue;
            }

            Map<String, Set<String>> offsets = new LinkedHashMap<>();
            List<String> evidence = new ArrayList<>();
            boolean hasIndirectBranch = false;
            boolean hasSmallKindTest = false;
            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (iterator.hasNext()) {
                Instruction instruction = iterator.next();
                String text = instruction.toString().toLowerCase(Locale.ROOT)
                    .replace(" ", "");
                String firstOperand = instruction.getNumOperands() > 0
                    ? instruction.getDefaultOperandRepresentation(0).toLowerCase(Locale.ROOT)
                        .replace(" ", "")
                    : "";
                Matcher matcher = FIELD.matcher(text);
                while (matcher.find()) {
                    String fieldText = matcher.group(0);
                    if (instruction.getMnemonicString().equalsIgnoreCase("MOV") &&
                        firstOperand.contains(fieldText)) {
                        continue;
                    }
                    if (matcher.group(2).equals("4") &&
                        !(text.contains("dwordptr" + fieldText) ||
                          instruction.getMnemonicString().equalsIgnoreCase("CMP"))) {
                        continue;
                    }
                    if (matcher.group(2).equals("8") &&
                        !text.contains("qwordptr" + fieldText)) {
                        continue;
                    }
                    offsets.computeIfAbsent(matcher.group(1), ignored -> new LinkedHashSet<>())
                        .add(matcher.group(2));
                    if (evidence.size() < 80) {
                        evidence.add(instruction.getAddress() + " " + instruction);
                    }
                }
                String mnemonic = instruction.getMnemonicString().toLowerCase(Locale.ROOT);
                if ((mnemonic.equals("call") || mnemonic.equals("jmp")) &&
                    text.contains("[")) {
                    hasIndirectBranch = true;
                }
                if ((mnemonic.equals("cmp") || mnemonic.equals("sub")) &&
                    text.matches(".*,(?:0x)?(?:[0-9a-f]|[12][0-9a-f]|3[0-9a-f])$")) {
                    hasSmallKindTest = true;
                }
            }

            Set<String> matchingBases = new LinkedHashSet<>();
            for (Map.Entry<String, Set<String>> value : offsets.entrySet()) {
                if (value.getValue().contains("4") && value.getValue().contains("8")) {
                    matchingBases.add(value.getKey());
                }
            }
            if (matchingBases.isEmpty() || (!hasIndirectBranch && !hasSmallKindTest)) {
                continue;
            }
            println("=== EFFECT_WRAPPER_DISPATCHER " + function.getName() + " " +
                function.getEntryPoint() + " BASES=" + matchingBases +
                " INDIRECT=" + hasIndirectBranch + " SMALL_TEST=" + hasSmallKindTest + " ===");
            for (String line : evidence) {
                println(line);
            }
            count++;
        }
        println("=== CANDIDATE_COUNT " + count + " ===");
    }
}
