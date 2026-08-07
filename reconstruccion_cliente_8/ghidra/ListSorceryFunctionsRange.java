// List functions intersecting an explicit address interval.
// Usage: ListSorceryFunctionsRange.java <start> <end>
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class ListSorceryFunctionsRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected start and end");
        }
        Address start = toAddr(args[0]);
        Address end = toAddr(args[1]);
        FunctionIterator iterator = currentProgram.getFunctionManager()
            .getFunctions(start, true);
        while (iterator.hasNext() && !monitor.isCancelled()) {
            Function function = iterator.next();
            if (function.getEntryPoint().compareTo(end) > 0) {
                break;
            }
            println(function.getEntryPoint() + " size=" +
                function.getBody().getNumAddresses() + " " +
                function.getName(true));
        }
    }
}
