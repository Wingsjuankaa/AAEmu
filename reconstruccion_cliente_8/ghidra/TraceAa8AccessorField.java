// Trace one field offset from the value returned by an accessor.
// Usage: TraceAa8AccessorField.java <output> <accessor> <field-offset>
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;

public class TraceAa8AccessorField extends GhidraScript {
    private static class State {
        final Varnode node;
        final long offset;

        State(Varnode node, long offset) {
            this.node = node;
            this.offset = offset;
        }
    }

    private static String key(Varnode node, long offset) {
        return node.toString() + ":" + Long.toUnsignedString(offset);
    }

    private static Long constant(Varnode node) {
        if (node != null && node.isConstant()) {
            return node.getOffset();
        }
        return null;
    }

    private static Address callTarget(PcodeOp op) {
        if (op.getNumInputs() == 0) {
            return null;
        }
        Varnode target = op.getInput(0);
        return target == null ? null : target.getAddress();
    }

    private static String functionName(
            Listing listing, Address address) {
        if (address == null) {
            return "indirect";
        }
        Function function = listing.getFunctionAt(address);
        return function == null ? address.toString() : function.getName();
    }

    private static void enqueue(
            ArrayDeque<State> queue,
            Set<String> seen,
            Varnode node,
            long offset) {
        if (node == null) {
            return;
        }
        String key = key(node, offset);
        if (seen.add(key)) {
            queue.addLast(new State(node, offset));
        }
    }

    private static List<String> trace(
            Listing listing,
            Function caller,
            HighFunction high,
            Address accessorAddress,
            long requestedOffset) {
        List<String> events = new ArrayList<>();
        Iterator<PcodeOpAST> operations = high.getPcodeOps();
        int seeds = 0;
        while (operations.hasNext()) {
            PcodeOpAST operation = operations.next();
            if (operation.getOpcode() != PcodeOp.CALL ||
                !accessorAddress.equals(callTarget(operation)) ||
                operation.getOutput() == null) {
                continue;
            }
            seeds++;
            ArrayDeque<State> queue = new ArrayDeque<>();
            Set<String> seen = new HashSet<>();
            enqueue(queue, seen, operation.getOutput(), 0);
            while (!queue.isEmpty()) {
                State state = queue.removeFirst();
                Iterator<PcodeOp> descendants =
                    state.node.getDescendants();
                while (descendants.hasNext()) {
                    PcodeOp descendant = descendants.next();
                    int opcode = descendant.getOpcode();
                    if (opcode == PcodeOp.COPY ||
                        opcode == PcodeOp.CAST ||
                        opcode == PcodeOp.INDIRECT ||
                        opcode == PcodeOp.MULTIEQUAL) {
                        enqueue(
                            queue, seen, descendant.getOutput(),
                            state.offset);
                        continue;
                    }
                    if (opcode == PcodeOp.INT_ADD ||
                        opcode == PcodeOp.PTRSUB) {
                        Long delta = null;
                        if (descendant.getInput(0) == state.node) {
                            delta = constant(descendant.getInput(1));
                        }
                        else if (opcode == PcodeOp.INT_ADD &&
                                 descendant.getInput(1) == state.node) {
                            delta = constant(descendant.getInput(0));
                        }
                        if (delta != null) {
                            long resultOffset = state.offset + delta;
                            enqueue(
                                queue, seen, descendant.getOutput(),
                                resultOffset);
                            if (resultOffset == requestedOffset) {
                                events.add(
                                    "FIELD_ADDRESS\t" +
                                    descendant.getSeqnum().getTarget() +
                                    "\t" + descendant);
                            }
                        }
                        continue;
                    }
                    if (opcode == PcodeOp.PTRADD &&
                        descendant.getInput(0) == state.node) {
                        Long index = constant(descendant.getInput(1));
                        Long stride = constant(descendant.getInput(2));
                        if (index != null && stride != null) {
                            long resultOffset =
                                state.offset + index * stride;
                            enqueue(
                                queue, seen, descendant.getOutput(),
                                resultOffset);
                            if (resultOffset == requestedOffset) {
                                events.add(
                                    "FIELD_ADDRESS\t" +
                                    descendant.getSeqnum().getTarget() +
                                    "\t" + descendant);
                            }
                        }
                        continue;
                    }
                    if (opcode == PcodeOp.LOAD &&
                        descendant.getNumInputs() > 1 &&
                        descendant.getInput(1) == state.node) {
                        events.add(
                            (state.offset == requestedOffset
                                ? "FIELD_LOAD"
                                : "OTHER_LOAD") +
                            "\t" + descendant.getSeqnum().getTarget() +
                            "\toffset=0x" +
                            Long.toHexString(state.offset) +
                            "\t" + descendant);
                        continue;
                    }
                    if ((opcode == PcodeOp.CALL ||
                         opcode == PcodeOp.CALLIND) &&
                        descendant.getNumInputs() > 1) {
                        for (int input = 1;
                             input < descendant.getNumInputs();
                             input++) {
                            if (descendant.getInput(input) == state.node) {
                                Address target = callTarget(descendant);
                                events.add(
                                    "FORWARDED_CALL\t" +
                                    descendant.getSeqnum().getTarget() +
                                    "\t" +
                                    functionName(listing, target) +
                                    "\targument=" + input +
                                    "\toffset=0x" +
                                    Long.toHexString(state.offset));
                            }
                        }
                    }
                }
            }
        }
        events.add(0, "ACCESSOR_CALL_SEEDS\t" + seeds);
        return events;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) {
            throw new IllegalArgumentException(
                "Expected: output, accessor address and field offset");
        }
        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        Address requested = toAddr(args[1]);
        long requestedOffset = Long.decode(args[2]);
        Listing listing = currentProgram.getListing();
        Function accessor = listing.getFunctionContaining(requested);
        if (accessor == null) {
            throw new IllegalArgumentException(
                "No function contains accessor " + requested);
        }
        List<Function> callers =
            new ArrayList<>(accessor.getCallingFunctions(monitor));
        callers.sort(
            Comparator.comparing(
                function -> function.getEntryPoint().getOffset()));

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        int fieldLoads = 0;
        int forwardedCalls = 0;
        int failures = 0;
        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("FORMAT\tAA8_ACCESSOR_FIELD_TRACE_V1");
            out.println("PROGRAM\t" + currentProgram.getName());
            out.println("IMAGE_BASE\t" + currentProgram.getImageBase());
            out.println(
                "ACCESSOR\t" + accessor.getName() + "\t" +
                accessor.getEntryPoint());
            out.println(
                "FIELD_OFFSET\t0x" +
                Long.toHexString(requestedOffset));
            out.println("CALLER_COUNT\t" + callers.size());
            for (Function caller : callers) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result =
                    decompiler.decompileFunction(caller, 180, monitor);
                if (!result.decompileCompleted() ||
                    result.getHighFunction() == null) {
                    failures++;
                    out.println(
                        "DECOMPILE_ERROR\t" + caller.getName() +
                        "\t" + caller.getEntryPoint() + "\t" +
                        result.getErrorMessage().replace('\n', ' '));
                    continue;
                }
                List<String> events = trace(
                    listing,
                    caller,
                    result.getHighFunction(),
                    accessor.getEntryPoint(),
                    requestedOffset);
                boolean relevant = false;
                for (String event : events) {
                    if (event.startsWith("FIELD_LOAD")) {
                        fieldLoads++;
                        relevant = true;
                    }
                    if (event.startsWith("FORWARDED_CALL")) {
                        forwardedCalls++;
                        relevant = true;
                    }
                }
                if (relevant) {
                    out.println();
                    out.println(
                        "CALLER_BEGIN\t" + caller.getName() +
                        "\t" + caller.getEntryPoint());
                    for (String event : events) {
                        out.println(event);
                    }
                    out.println(result.getDecompiledFunction().getC());
                    out.println("CALLER_END");
                }
            }
            out.println("FIELD_LOADS\t" + fieldLoads);
            out.println("FORWARDED_CALLS\t" + forwardedCalls);
            out.println("DECOMPILE_FAILURES\t" + failures);
        }
        finally {
            decompiler.dispose();
        }
        println("Wrote " + output.getAbsolutePath());
    }
}
