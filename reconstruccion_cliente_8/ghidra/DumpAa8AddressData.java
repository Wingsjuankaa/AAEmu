// Dump the defined data and direct references for explicit addresses.
// Usage: DumpAa8AddressData.java <output> <address> [...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class DumpAa8AddressData extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Expected: output and at least one address");
        }
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }

        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        Set<Function> referencingFunctions = new LinkedHashSet<>();
        List<String> records = new ArrayList<>();
        for (int index = 1; index < args.length; index++) {
            Address address = toAddr(args[index]);
            Data data = listing.getDataAt(address);
            if (data == null) {
                data = listing.getDataContaining(address);
            }
            StringBuilder cString = new StringBuilder();
            for (int offset = 0; offset < 512; offset++) {
                byte value = memory.getByte(address.add(offset));
                if (value == 0) {
                    break;
                }
                int unsigned = value & 0xff;
                if (unsigned >= 0x20 && unsigned <= 0x7e) {
                    cString.append((char)unsigned);
                }
                else {
                    cString.append(
                        String.format("\\x%02x", unsigned));
                }
            }
            records.add(
                "ADDRESS\t" + address +
                "\tDATA_ADDRESS\t" +
                (data == null ? "none" : data.getAddress()) +
                "\tTYPE\t" +
                (data == null ? "none" : data.getDataType().getName()) +
                "\tVALUE\t" +
                (data == null ? "none" : String.valueOf(data.getValue())) +
                "\tREPRESENTATION\t" +
                (data == null ? "none" : data.getDefaultValueRepresentation()) +
                "\tC_STRING\t" + cString);
            ReferenceIterator references =
                currentProgram.getReferenceManager().getReferencesTo(address);
            while (references.hasNext()) {
                Reference reference = references.next();
                Function function =
                    listing.getFunctionContaining(reference.getFromAddress());
                records.add(
                    "REFERENCE\t" + address + "\t" +
                    reference.getFromAddress() + "\t" +
                    reference.getReferenceType() + "\t" +
                    (function == null
                        ? "none"
                        : function.getName() + "@" +
                          function.getEntryPoint()));
                if (function != null) {
                    referencingFunctions.add(function);
                }
            }
        }

        List<Function> functions = new ArrayList<>(referencingFunctions);
        functions.sort(
            Comparator.comparing(function -> function.getEntryPoint()));
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_ADDRESS_DATA_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            for (String record : records) {
                out.println(record);
            }
            for (Function function : functions) {
                DecompileResults result =
                    decompiler.decompileFunction(function, 180, monitor);
                out.println();
                out.println(
                    "FUNCTION_BEGIN\t" + function.getName() + "\t" +
                    function.getEntryPoint());
                if (result.decompileCompleted() &&
                    result.getDecompiledFunction() != null) {
                    out.println(result.getDecompiledFunction().getC());
                }
                else {
                    out.println(
                        "DECOMPILE_ERROR\t" +
                        result.getErrorMessage().replace('\n', ' '));
                }
                out.println("FUNCTION_END");
            }
        }
        finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
