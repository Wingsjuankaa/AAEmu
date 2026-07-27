// Find AA8 strings by substring and decompile every direct referencing function.
// Input is UTF-8 TSV with: label<TAB>case-sensitive substring
// Usage: DumpAa8StringConsumers.java <output> <task-tsv>
// @category AA8

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.util.DefinedDataIterator;

public class DumpAa8StringConsumers extends GhidraScript {
    private static class Task {
        final String label;
        final String needle;

        Task(String label, String needle) {
            this.label = label;
            this.needle = needle;
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Expected: output file and UTF-8 task TSV");
        }
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        List<Task> tasks = readTasks(new File(args[1]));
        Listing listing = currentProgram.getListing();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_STRING_CONSUMERS_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            for (Task task : tasks) {
                out.println();
                out.println("TASK\t" + task.label);
                out.println("NEEDLE\t" + task.needle);
                List<Data> matches = findStrings(task.needle);
                out.println("STRING_MATCHES\t" + matches.size());
                Set<Address> dumpedFunctions = new HashSet<>();
                for (Data data : matches) {
                    out.println(
                        "STRING\t" + data.getAddress() + "\t" +
                        String.valueOf(data.getValue()).replace('\n', ' '));
                    ReferenceIterator references = currentProgram
                        .getReferenceManager().getReferencesTo(data.getAddress());
                    while (references.hasNext()) {
                        Reference reference = references.next();
                        Address from = reference.getFromAddress();
                        Function function = listing.getFunctionContaining(from);
                        out.println(
                            "REFERENCE\t" + from + "\t" +
                            reference.getReferenceType() + "\t" +
                            (function == null
                                ? "<none>"
                                : function.getName() + "@" +
                                  function.getEntryPoint()));
                        if (function == null ||
                            !dumpedFunctions.add(function.getEntryPoint())) {
                            continue;
                        }
                        out.println(
                            "FUNCTION_BEGIN\t" + function.getName() + "\t" +
                            function.getEntryPoint());
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
                }
                out.println("TASK_END");
            }
        } finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }

    private List<Task> readTasks(File input) throws Exception {
        List<Task> tasks = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(
                 new InputStreamReader(
                     new FileInputStream(input), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty() || line.startsWith("#")) {
                    continue;
                }
                int separator = line.indexOf('\t');
                if (separator <= 0 || separator == line.length() - 1) {
                    throw new IllegalArgumentException(
                        "Invalid task TSV line: " + line);
                }
                tasks.add(new Task(
                    line.substring(0, separator),
                    line.substring(separator + 1)));
            }
        }
        return tasks;
    }

    private List<Data> findStrings(String needle) {
        List<Data> result = new ArrayList<>();
        for (Data data : DefinedDataIterator.byDataInstance(
                 currentProgram,
                 candidate -> candidate.getValue() instanceof String)) {
            String text = String.valueOf(data.getValue());
            if (text.contains(needle)) {
                result.add(data);
            }
        }
        return result;
    }
}
