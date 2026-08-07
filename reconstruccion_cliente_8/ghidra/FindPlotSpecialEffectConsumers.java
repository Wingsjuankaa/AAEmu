// Find functions that test a polymorphic plot/effect kind against 0x17
// (SpecialEffect in the retail plot-effect loader), and print nearby code.
// Usage: FindPlotSpecialEffectConsumers.java [context-instructions]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.util.LinkedHashSet;
import java.util.Set;

public class FindPlotSpecialEffectConsumers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int context = args.length > 0 ? Integer.parseInt(args[0]) : 16;
        Set<Function> matches = new LinkedHashSet<>();

        InstructionIterator all = currentProgram.getListing().getInstructions(true);
        while (all.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = all.next();
            String text = instruction.toString().toLowerCase().replace(" ", "");
            if (!text.startsWith("cmp") || !text.contains("+0x4],0x17")) {
                continue;
            }
            if (!(text.contains("[r") || text.contains("[e"))) {
                continue;
            }
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            if (owner != null) {
                matches.add(owner);
            }
        }

        for (Function function : matches) {
            println("=== PLOT_SPECIAL_EFFECT_CONSUMER " + function.getName() + " " +
                function.getEntryPoint() + " ===");
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                String text = instruction.toString().toLowerCase().replace(" ", "");
                if (!text.startsWith("cmp") || !text.contains("+0x4],0x17")) {
                    continue;
                }
                Address cursor = instruction.getAddress();
                for (int index = 0; index < context; index++) {
                    Instruction previous = currentProgram.getListing().getInstructionBefore(cursor);
                    if (previous == null || !function.getBody().contains(previous.getAddress())) {
                        break;
                    }
                    cursor = previous.getAddress();
                }
                for (int index = 0; index < context * 2 + 1; index++) {
                    Instruction line = currentProgram.getListing().getInstructionAt(cursor);
                    if (line == null || !function.getBody().contains(cursor)) {
                        break;
                    }
                    println(cursor + " " + line);
                    Instruction next = currentProgram.getListing().getInstructionAfter(cursor);
                    if (next == null) {
                        break;
                    }
                    cursor = next.getAddress();
                }
            }
        }
        println("=== CONSUMER_COUNT " + matches.size() + " ===");
    }
}
