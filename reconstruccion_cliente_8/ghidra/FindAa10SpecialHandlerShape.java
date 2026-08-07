// Locate x64 functions shaped like a SpecialEffectDesc handler.
// The ABI for a 12-byte SkillResult uses RCX as hidden return storage and RDX
// as SpecialEffectDesc const*.  This script follows only simple register aliases
// established in the prologue and requires reads of value1..value4.
// Usage: FindAa10SpecialHandlerShape.java [instruction-limit] [min-address] [max-address]
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
import java.util.Locale;
import java.util.Set;

public class FindAa10SpecialHandlerShape extends GhidraScript {
    private static final List<String> OFFSETS = Arrays.asList("0x4", "0x8", "0xc", "0x10");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int limit = args.length > 0 ? Integer.parseInt(args[0]) : 220;
        long minimumAddress = args.length > 1 ? Long.parseUnsignedLong(args[1], 16) : 0;
        long maximumAddress = args.length > 2
            ? Long.parseUnsignedLong(args[2], 16)
            : Long.MAX_VALUE;
        int count = 0;
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            long entry = function.getEntryPoint().getOffset();
            if (Long.compareUnsigned(entry, minimumAddress) < 0 ||
                Long.compareUnsigned(entry, maximumAddress) >= 0) {
                continue;
            }
            Set<String> aliases = new LinkedHashSet<>();
            aliases.add("rdx");
            aliases.add("edx");
            Set<String> reads = new LinkedHashSet<>();
            List<String> evidence = new ArrayList<>();
            boolean returnsHidden = false;

            InstructionIterator iterator = currentProgram.getListing().getInstructions(function.getBody(), true);
            int seen = 0;
            while (iterator.hasNext() && seen++ < limit) {
                Instruction instruction = iterator.next();
                String mnemonic = instruction.getMnemonicString().toLowerCase(Locale.ROOT);
                String text = instruction.toString().toLowerCase(Locale.ROOT).replace(" ", "");

                // Record reads before alias invalidation.  A memory destination in
                // MOV is a write and must not count as descriptor consumption.
                String destination = instruction.getNumOperands() > 0
                    ? instruction.getDefaultOperandRepresentation(0).toLowerCase(Locale.ROOT).replace(" ", "")
                    : "";
                for (String alias : new ArrayList<>(aliases)) {
                    for (String offset : OFFSETS) {
                        String needle = "[" + alias + "+" + offset + "]";
                        if (!text.contains(needle)) {
                            continue;
                        }
                        if (mnemonic.startsWith("mov") && destination.contains(needle)) {
                            continue;
                        }
                        reads.add(offset);
                        if (evidence.size() < 40) {
                            evidence.add(instruction.getAddress() + " " + instruction);
                        }
                    }
                }

                if ((text.startsWith("movrax,rcx") || text.startsWith("movrax,") && text.endsWith("rcx")) ||
                    text.contains("[rcx+0x8]") || text.contains("[rcx+0x4]")) {
                    returnsHidden = true;
                }

                // Maintain only simple register aliases for MOV/LEA.  Any other
                // assignment to a register invalidates an earlier alias.
                if (instruction.getNumOperands() >= 1 && !destination.contains("[") &&
                    (destination.startsWith("r") || destination.startsWith("e"))) {
                    String source = instruction.getNumOperands() >= 2
                        ? instruction.getDefaultOperandRepresentation(1).toLowerCase(Locale.ROOT).replace(" ", "")
                        : "";
                    boolean fromAlias = false;
                    if (mnemonic.equals("mov") || mnemonic.equals("lea")) {
                        for (String alias : new ArrayList<>(aliases)) {
                            if (source.equals(alias) || source.equals("[" + alias + "]")) {
                                fromAlias = true;
                                break;
                            }
                        }
                    }
                    if (fromAlias) {
                        aliases.add(destination);
                    }
                    else if (!destination.equals("rdx") && !destination.equals("edx")) {
                        aliases.remove(destination);
                    }
                }
            }

            if (!reads.containsAll(OFFSETS) || !returnsHidden) {
                continue;
            }
            println("=== AA10_SPECIAL_HANDLER_SHAPE " + function.getName() + " " +
                function.getEntryPoint() + " READS=" + String.join(",", reads) + " ===");
            for (String line : evidence) {
                println(line);
            }
            count++;
        }
        println("=== AA10_SPECIAL_HANDLER_SHAPE_COUNT " + count + " ===");
    }
}
