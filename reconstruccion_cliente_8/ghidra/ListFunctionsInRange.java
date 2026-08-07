// List discovered functions whose entry points fall inside a virtual range.
// Usage: ListFunctionsInRange.java <start-address> <end-address>
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

public class ListFunctionsInRange extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Expected start-address and end-address");
        }
        Address start = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Address end = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[1]);
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(start, true);
        while (functions.hasNext()) {
            Function function = functions.next();
            if (function.getEntryPoint().compareTo(end) >= 0) {
                break;
            }
            println(function.getEntryPoint() + " " + function.getName() +
                " SIZE=" + function.getBody().getNumAddresses());
        }
    }
}
