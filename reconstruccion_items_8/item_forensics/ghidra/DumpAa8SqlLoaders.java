// Find exact embedded AA8 SQL strings and decompile every referencing loader.
// Input is UTF-8 TSV with: table_name<TAB>exact SQL text
// Usage: DumpAa8SqlLoaders.java <output> <task-tsv>
// @category AA8

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
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

public class DumpAa8SqlLoaders extends GhidraScript {
    private static class Task {
        final String table;
        final String sql;

        Task(String table, String sql) {
            this.table = table;
            this.sql = sql;
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
        Map<String, List<Address>> strings = indexDefinedStrings(tasks);
        Listing listing = currentProgram.getListing();
        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_SQL_LOADERS_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            out.println("LANGUAGE\t" + currentProgram.getLanguageID());

            for (Task task : tasks) {
                out.println();
                out.println("TASK\t" + task.table);
                out.println("SQL\t" + task.sql);
                List<Address> addresses =
                    strings.getOrDefault(task.sql, new ArrayList<Address>());
                out.println("STRING_MATCHES\t" + addresses.size());
                Set<Address> dumpedFunctions = new HashSet<>();

                for (Address address : addresses) {
                    out.println("STRING_ADDRESS\t" + address);
                    ReferenceIterator references = currentProgram
                        .getReferenceManager().getReferencesTo(address);
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

    private Map<String, List<Address>> indexDefinedStrings(List<Task> tasks) {
        Set<String> wanted = new HashSet<>();
        for (Task task : tasks) {
            wanted.add(task.sql);
        }

        Map<String, List<Address>> result = new HashMap<>();
        for (Data data : DefinedDataIterator.byDataInstance(
                 currentProgram,
                 candidate -> candidate.getValue() instanceof String)) {
            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }
            String text = (String)value;
            if (!wanted.contains(text)) {
                continue;
            }
            result.computeIfAbsent(text, key -> new ArrayList<Address>())
                .add(data.getAddress());
        }
        return result;
    }
}
