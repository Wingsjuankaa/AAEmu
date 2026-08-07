// Find functions that both recognize polymorphic plot SpecialEffect (kind
// 0x17 at plot-effect+4) and compare the nested SpecialEffectDesc type with a
// requested integer.  This isolates direct semantic consumers of one type.
// Usage: FindSpecialTypeConsumers.java <type-hex> [context-instructions]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.util.ArrayList;
import java.util.List;

public class FindSpecialTypeConsumers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Expected special effect type in hex");
        }
        String wanted = args[0].toLowerCase();
        if (!wanted.startsWith("0x")) {
            wanted = "0x" + wanted;
        }
        int context = args.length > 1 ? Integer.parseInt(args[1]) : 20;
        int count = 0;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            List<Instruction> lines = new ArrayList<>();
            boolean seesPlotSpecial = false;
            boolean seesWanted = false;
            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (iterator.hasNext()) {
                Instruction instruction = iterator.next();
                lines.add(instruction);
                String text = instruction.toString().toLowerCase().replace(" ", "");
                if (text.startsWith("cmp") && text.contains("+0x4],0x17")) {
                    seesPlotSpecial = true;
                }
                if ((text.startsWith("cmp") || text.startsWith("sub")) &&
                    text.endsWith("," + wanted)) {
                    seesWanted = true;
                }
            }
            if (!seesPlotSpecial || !seesWanted) {
                continue;
            }
            println("=== SPECIAL_TYPE_CONSUMER " + function.getName() + " " +
                function.getEntryPoint() + " TYPE=" + wanted + " ===");
            for (int index = 0; index < lines.size(); index++) {
                String text = lines.get(index).toString().toLowerCase().replace(" ", "");
                if (!text.endsWith("," + wanted)) {
                    continue;
                }
                int start = Math.max(0, index - context);
                int end = Math.min(lines.size(), index + context + 1);
                for (int line = start; line < end; line++) {
                    println(lines.get(line).getAddress() + " " + lines.get(line));
                }
            }
            count++;
        }
        println("=== CONSUMER_COUNT " + count + " ===");
    }
}
