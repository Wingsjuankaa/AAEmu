// Decompile functions in an address range and retain functions containing all
// required text tokens. Prefix a token with "?" to make it optional: at least
// one optional token must match when optional tokens are supplied.
// Usage: DumpAa8RangeTokenMatches.java <output> <start> <end> <token> [...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class DumpAa8RangeTokenMatches extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 4) {
            throw new IllegalArgumentException(
                "Expected: output, start, end and at least one token");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        Address start = toAddr(args[1]);
        Address end = toAddr(args[2]);
        List<String> required = new ArrayList<>();
        List<String> optional = new ArrayList<>();
        for (int index = 3; index < args.length; index++) {
            if (args[index].startsWith("?")) {
                optional.add(args[index].substring(1));
            }
            else {
                required.add(args[index]);
            }
        }

        List<Function> functions = new ArrayList<>();
        FunctionIterator iterator =
            currentProgram.getFunctionManager().getFunctions(start, true);
        while (iterator.hasNext()) {
            Function function = iterator.next();
            if (function.getEntryPoint().compareTo(end) >= 0) {
                break;
            }
            functions.add(function);
        }
        functions.sort(
            Comparator.comparing(function -> function.getEntryPoint()));

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        int matched = 0;
        int failed = 0;
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_RANGE_TOKEN_MATCHES_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            out.println("RANGE\t" + start + "\t" + end);
            out.println("FUNCTION_COUNT\t" + functions.size());
            for (String token : required) {
                out.println("REQUIRED_TOKEN\t" + token);
            }
            for (String token : optional) {
                out.println("OPTIONAL_TOKEN\t" + token);
            }

            for (Function function : functions) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result =
                    decompiler.decompileFunction(function, 180, monitor);
                if (!result.decompileCompleted() ||
                    result.getDecompiledFunction() == null) {
                    failed++;
                    continue;
                }
                String code = result.getDecompiledFunction().getC();
                boolean keep = true;
                for (String token : required) {
                    if (!code.contains(token)) {
                        keep = false;
                        break;
                    }
                }
                if (!keep) {
                    continue;
                }
                if (!optional.isEmpty()) {
                    boolean optionalHit = false;
                    for (String token : optional) {
                        if (code.contains(token)) {
                            optionalHit = true;
                            break;
                        }
                    }
                    if (!optionalHit) {
                        continue;
                    }
                }
                matched++;
                out.println();
                out.println(
                    "FUNCTION_BEGIN\t" + function.getName() + "\t" +
                    function.getEntryPoint());
                out.println(code);
                out.println("FUNCTION_END");
            }
            out.println("MATCHED_FUNCTIONS\t" + matched);
            out.println("DECOMPILE_FAILURES\t" + failed);
        }
        finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
