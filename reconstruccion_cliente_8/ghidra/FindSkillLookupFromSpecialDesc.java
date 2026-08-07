// Find callers of the retail skill descriptor lookup whose decompiled body
// also consumes value1/value2/value3 from one SpecialEffectDesc base.  The
// descriptor payload layout is: type@0, value1@4, value2@8, value3@0xc,
// value4@0x10.  This semantic intersection is much narrower than scanning
// arbitrary x64 memory offsets.
// Usage: FindSkillLookupFromSpecialDesc.java <lookup-address> [timeout-seconds]
// @category AA8

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.util.LinkedHashSet;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class FindSkillLookupFromSpecialDesc extends GhidraScript {
    private static final Pattern VALUE1 = Pattern.compile(
        "\\*\\([^)]*\\*\\)\\(([_A-Za-z][_A-Za-z0-9]*) \\+ 4\\)");

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            throw new IllegalArgumentException("Expected skill lookup address");
        }
        int timeout = args.length > 1 ? Integer.parseInt(args[1]) : 60;
        Address lookup = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(args[0]);
        Set<Function> callers = new LinkedHashSet<>();
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(lookup);
        while (references.hasNext()) {
            Reference reference = references.next();
            if (!reference.getReferenceType().isCall()) {
                continue;
            }
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            if (owner != null) {
                callers.add(owner);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.setSimplificationStyle("decompile");
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException(decompiler.getLastMessage());
        }
        int matches = 0;
        try {
            for (Function function : callers) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result = decompiler.decompileFunction(
                    function, timeout, monitor);
                if (!result.decompileCompleted()) {
                    continue;
                }
                String code = result.getDecompiledFunction().getC();
                Matcher matcher = VALUE1.matcher(code);
                Set<String> bases = new LinkedHashSet<>();
                while (matcher.find()) {
                    String base = matcher.group(1);
                    if (code.contains("*(int *)(" + base + " + 8)") &&
                        code.contains("*(int *)(" + base + " + 0xc)")) {
                        bases.add(base);
                    }
                }
                if (bases.isEmpty()) {
                    continue;
                }
                println("=== SKILL_LOOKUP_SPECIAL_DESC " + function.getName() + " " +
                    function.getEntryPoint() + " BASES=" + bases + " ===");
                println(code);
                println("=== END_SKILL_LOOKUP_SPECIAL_DESC ===");
                matches++;
            }
        }
        finally {
            decompiler.dispose();
        }
        println("=== CALLERS " + callers.size() + " MATCHES " + matches + " ===");
    }
}
