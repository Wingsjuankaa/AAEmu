// Find x64 functions whose early instructions consume several fields from the
// SpecialEffectDesc argument.  The retail callback ABI returns SkillResult in
// RCX and receives SpecialEffectDesc const* in RDX, so RDX and simple register
// aliases are followed through the function prologue.
// Usage: FindSpecialEffectHandlers.java [minimum-fields] [instruction-limit]
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
import java.util.Set;

public class FindSpecialEffectHandlers extends GhidraScript {
    private static final List<String> DESC_OFFSETS = Arrays.asList(
        "0x4", "0x8", "0xc", "0x10", "0x14", "0x18", "0x1c");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        int minimum = args.length > 0 ? Integer.parseInt(args[0]) : 2;
        int limit = args.length > 1 ? Integer.parseInt(args[1]) : 160;

        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        int candidates = 0;
        while (functions.hasNext() && !monitor.isCancelled()) {
            Function function = functions.next();
            Set<String> aliases = new LinkedHashSet<>();
            aliases.add("rdx");
            aliases.add("edx");
            Set<String> offsets = new LinkedHashSet<>();
            List<String> examples = new ArrayList<>();

            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            int seen = 0;
            while (iterator.hasNext() && seen++ < limit) {
                Instruction instruction = iterator.next();
                String rendered = instruction.toString().toLowerCase().replace(" ", "");

                // Follow the common prologue forms MOV r64,RDX and LEA r64,[RDX].
                if (rendered.startsWith("mov") || rendered.startsWith("lea")) {
                    int comma = rendered.indexOf(',');
                    if (comma > 3) {
                        String destination = rendered.substring(3, comma)
                            .replace("qwordptr", "").replace("dwordptr", "");
                        String source = rendered.substring(comma + 1);
                        for (String alias : new ArrayList<>(aliases)) {
                            if (source.equals(alias) || source.equals("[" + alias + "]")) {
                                aliases.add(destination);
                            }
                        }
                    }
                }

                for (String alias : aliases) {
                    for (String offset : DESC_OFFSETS) {
                        if (rendered.contains("[" + alias + "+" + offset + "]")) {
                            offsets.add(offset);
                            if (examples.size() < 24) {
                                examples.add(instruction.getAddress() + " " + instruction);
                            }
                        }
                    }
                }
            }

            if (offsets.size() < minimum) {
                continue;
            }
            println("=== SPECIAL_EFFECT_HANDLER_CANDIDATE " + function.getName() + " " +
                function.getEntryPoint() + " FIELDS=" + String.join(",", offsets) + " ===");
            for (String example : examples) {
                println(example);
            }
            candidates++;
        }
        println("=== CANDIDATE_COUNT " + candidates + " ===");
    }
}
