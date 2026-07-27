// Dump pointer-sized entries around explicit AA8 addresses and decompile
// function targets. Usage: DumpAa8PointerTable.java <output> <before>
// <after> <address> [address...]
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
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;

public class DumpAa8PointerTable extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 4) {
            throw new IllegalArgumentException(
                "Expected: output, entries before, entries after, addresses");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        int before = Integer.parseInt(args[1]);
        int after = Integer.parseInt(args[2]);
        Memory memory = currentProgram.getMemory();
        Set<Address> dumpedFunctions = new HashSet<>();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM " + currentProgram.getName());
            out.println("IMAGE_BASE " + currentProgram.getImageBase());

            for (int argIndex = 3; argIndex < args.length; argIndex++) {
                Address center = toAddr(args[argIndex]);
                out.println();
                out.println("===== POINTERS AROUND " + center + " =====");

                for (int index = -before; index <= after; index++) {
                    Address slot = center.add((long) index * 8);
                    long raw = memory.getLong(slot);
                    Address target = currentProgram.getAddressFactory()
                        .getDefaultAddressSpace().getAddress(raw);
                    Function function =
                        currentProgram.getListing().getFunctionAt(target);
                    out.println(
                        "SLOT " + index + " " + slot + " -> " + target +
                        (function == null ? "" : " " + function.getName()));

                    if (function == null ||
                        !dumpedFunctions.add(function.getEntryPoint())) {
                        continue;
                    }

                    out.println();
                    out.println("----- " + function.getName() + " @ " +
                        function.getEntryPoint() + " -----");
                    DecompileResults result =
                        decompiler.decompileFunction(function, 120, monitor);
                    if (!result.decompileCompleted() ||
                        result.getDecompiledFunction() == null) {
                        out.println(
                            "DECOMPILE FAILED: " + result.getErrorMessage());
                    } else {
                        out.println(result.getDecompiledFunction().getC());
                    }
                }
            }
        } finally {
            decompiler.dispose();
        }

        println("Wrote " + output.getAbsolutePath());
    }
}
