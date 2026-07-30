// Dump every function entry and decompilation in an explicit address range.
// Usage: DumpAa8FunctionRange.java <output> <start-address> <end-address>
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class DumpAa8FunctionRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) {
            throw new IllegalArgumentException(
                "Expected: output file, start address, end address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        Address start = toAddr(args[1]);
        Address end = toAddr(args[2]);
        if (start.compareTo(end) > 0) {
            throw new IllegalArgumentException("Start address is after end address");
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        int count = 0;
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_FUNCTION_RANGE_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            out.println("RANGE\t" + start + "\t" + end);

            FunctionIterator functions =
                currentProgram.getFunctionManager().getFunctions(start, true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                Address entry = function.getEntryPoint();
                if (entry.compareTo(end) > 0) {
                    break;
                }
                count++;
                out.println();
                out.println(
                    "FUNCTION_BEGIN\t" + function.getName() + "\t" + entry);
                DecompileResults result =
                    decompiler.decompileFunction(function, 180, monitor);
                if (!result.decompileCompleted() ||
                    result.getDecompiledFunction() == null) {
                    out.println(
                        "DECOMPILE_ERROR\t" +
                        result.getErrorMessage().replace('\n', ' '));
                } else {
                    out.println(result.getDecompiledFunction().getC());
                }
                out.println("FUNCTION_END");
            }
            out.println("FUNCTION_COUNT\t" + count);
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
