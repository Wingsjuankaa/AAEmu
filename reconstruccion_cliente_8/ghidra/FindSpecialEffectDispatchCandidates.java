// Locate candidate special-effect dispatch/registration functions.
// A candidate must reference immediate type 33 and several other small type
// identifiers in MOV/CMP/PUSH instructions.  This deliberately ignores memory
// displacements and instruction-size scalars.
// Usage: FindSpecialEffectDispatchCandidates.java <minimum-distinct-types>
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class FindSpecialEffectDispatchCandidates extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int minimum = args.length == 0 ? 8 : Integer.parseInt(args[0]);
        Map<Function, Set<Long>> values = new LinkedHashMap<>();
        Map<Function, List<String>> examples = new LinkedHashMap<>();

        InstructionIterator iterator = currentProgram.getListing().getInstructions(true);
        while (iterator.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = iterator.next();
            String mnemonic = instruction.getMnemonicString().toUpperCase();
            if (!mnemonic.equals("MOV") && !mnemonic.equals("CMP") &&
                !mnemonic.equals("PUSH")) {
                continue;
            }
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            if (function == null) {
                continue;
            }
            boolean matched = false;
            for (int operand = 0; operand < instruction.getNumOperands(); operand++) {
                for (Object object : instruction.getOpObjects(operand)) {
                    if (!(object instanceof Scalar)) {
                        continue;
                    }
                    Scalar scalar = (Scalar)object;
                    long value = scalar.getUnsignedValue();
                    if (value < 1 || value > 220) {
                        continue;
                    }
                    values.computeIfAbsent(function, ignored -> new LinkedHashSet<>())
                        .add(value);
                    matched = true;
                }
            }
            if (matched) {
                examples.computeIfAbsent(function, ignored -> new ArrayList<>())
                    .add(instruction.getAddress() + " " + instruction);
            }
        }

        int count = 0;
        for (Map.Entry<Function, Set<Long>> entry : values.entrySet()) {
            if (!entry.getValue().contains(33L) || entry.getValue().size() < minimum) {
                continue;
            }
            Function function = entry.getKey();
            println("=== SPECIAL_EFFECT_DISPATCH_CANDIDATE " + function.getName() +
                " " + function.getEntryPoint() + " DISTINCT=" +
                entry.getValue().size() + " VALUES=" + entry.getValue() + " ===");
            List<String> lines = examples.get(function);
            int limit = Math.min(lines.size(), 300);
            for (int index = 0; index < limit; index++) {
                println(lines.get(index));
            }
            count++;
        }
        println("=== SPECIAL_EFFECT_DISPATCH_CANDIDATES " + count + " ===");
    }
}
