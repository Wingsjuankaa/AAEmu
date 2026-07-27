// Locate and decompile the native AA8 NPC interaction packet reader, its callers,
// and the native exports that expose NPC quest contexts to Lua.
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpAa8NpcInteractionFlow extends GhidraScript {
    private PrintWriter out;
    private DecompInterface decompiler;
    private final Set<Address> dumped = new HashSet<>();

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("Expected one argument: output file path");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        out = new PrintWriter(output, StandardCharsets.UTF_8.name());
        decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        out.println("PROGRAM " + currentProgram.getName());
        out.println("IMAGE_BASE " + currentProgram.getImageBase());
        out.println();

        dumpFunctionAndCallers(toAddr("3999db50"), 3, "SCNpcInteractionSkillList native reader");
        dumpVtable(toAddr("39cfaa48"), 20, "SCNpcInteractionSkillList vtable");
        dumpVtable(toAddr("39d0be90"), 12, "SCNpcInteractionSkillList dispatch-node vtable");
        dumpAllReferencesTo(toAddr("39333100"), "SCNpcInteractionSkillList factory");
        dumpFeatureBitConsumers(toAddr("3a10e778"));

        dumpFunctionsContainingAny(
            "GetNpcQuestContextCountStart",
            "GetNpcQuestContextCountComplete",
            "GetNpcQuestContextStart",
            "GetNpcQuestContextComplete",
            "CallQuestUi",
            "questNpcTag",
            "NPC_INTERACTION_START"
        );

        decompiler.dispose();
        out.close();
        println("Wrote " + output.getAbsolutePath());
    }

    private void dumpAllReferencesTo(Address address, String reason) {
        out.println();
        out.println("===== REFERENCES TO " + address + " =====");
        out.println("REASON " + reason);

        Listing listing = currentProgram.getListing();
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(address);
        while (refs.hasNext()) {
            Reference ref = refs.next();
            Address from = ref.getFromAddress();
            out.println("REF " + from + " " + ref.getReferenceType());
            Function containing = listing.getFunctionContaining(from);
            if (containing != null) {
                dumpFunction(containing, reason + " reference from " + from);
            }
        }
    }

    private void dumpFeatureBitConsumers(Address globalAddress) {
        out.println();
        out.println("===== QUEST NPC TAG FEATURE CONSUMERS =====");
        out.println("GLOBAL " + globalAddress + " offset 0x30 bit 0x40000000");

        Listing listing = currentProgram.getListing();
        Set<Address> seenFunctions = new HashSet<>();
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(globalAddress);
        while (refs.hasNext()) {
            Reference ref = refs.next();
            Function containing = listing.getFunctionContaining(ref.getFromAddress());
            if (containing == null || !seenFunctions.add(containing.getEntryPoint())) {
                continue;
            }

            DecompileResults result = decompiler.decompileFunction(containing, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                continue;
            }
            String code = result.getDecompiledFunction().getC();
            if (code.contains("0x40000000") && code.contains("DAT_3a10e778")) {
                dumpFunction(containing, "references feature-set global and bit 0x40000000");
            }
        }
    }

    private void dumpVtable(Address tableAddress, int entries, String reason) throws Exception {
        Memory memory = currentProgram.getMemory();
        out.println();
        out.println("===== VTABLE " + tableAddress + " =====");
        out.println("REASON " + reason);

        for (int i = 0; i < entries; i++) {
            Address slot = tableAddress.add((long) i * 8);
            long raw = memory.getLong(slot);
            Address target = currentProgram.getAddressFactory()
                .getDefaultAddressSpace()
                .getAddress(raw);
            out.println("SLOT " + i + " " + slot + " -> " + target);
            Function function = currentProgram.getListing().getFunctionAt(target);
            if (function != null) {
                dumpFunction(function, reason + " slot " + i);
            }
        }
    }

    private void dumpFunctionsContainingAny(String... needles) {
        Listing listing = currentProgram.getListing();
        for (Data data : listing.getDefinedData(true)) {
            if (monitor.isCancelled()) {
                return;
            }

            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }

            String text = (String) value;
            boolean matched = false;
            for (String needle : needles) {
                if (text.contains(needle)) {
                    matched = true;
                    break;
                }
            }
            if (!matched) {
                continue;
            }

            out.println();
            out.println("===== STRING " + data.getAddress() + " =====");
            out.println(text);

            ReferenceIterator refs = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (refs.hasNext()) {
                Reference ref = refs.next();
                Address from = ref.getFromAddress();
                out.println("REF " + from + " " + ref.getReferenceType());
                Function containing = listing.getFunctionContaining(from);
                if (containing != null) {
                    dumpFunctionAndCallers(containing.getEntryPoint(), 1, "string xref: " + text);
                }
            }
        }
    }

    private void dumpFunctionAndCallers(Address address, int callerDepth, String reason) {
        Listing listing = currentProgram.getListing();
        Function function = listing.getFunctionContaining(address);
        if (function == null) {
            function = listing.getFunctionAt(address);
        }
        if (function == null) {
            out.println("NO FUNCTION at " + address + " (" + reason + ")");
            return;
        }

        dumpFunction(function, reason);
        if (callerDepth <= 0) {
            return;
        }

        ReferenceIterator refs = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        while (refs.hasNext()) {
            Reference ref = refs.next();
            if (!ref.getReferenceType().isCall()) {
                continue;
            }
            Function caller = listing.getFunctionContaining(ref.getFromAddress());
            if (caller == null) {
                continue;
            }
            dumpFunctionAndCallers(
                caller.getEntryPoint(),
                callerDepth - 1,
                "caller of " + function.getName() + " from " + ref.getFromAddress()
            );
        }
    }

    private void dumpFunction(Function function, String reason) {
        if (!dumped.add(function.getEntryPoint())) {
            return;
        }

        out.println();
        out.println("===== FUNCTION " + function.getName() + " @ " +
            function.getEntryPoint() + " =====");
        out.println("REASON " + reason);

        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            out.println("DECOMPILE FAILED: " + result.getErrorMessage());
            return;
        }
        out.println(result.getDecompiledFunction().getC());
    }
}
