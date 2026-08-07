// Dump 32-bit RVA and 64-bit pointer interpretations around data addresses.
// Usage: DumpSorceryPointerWindow.java <before-bytes> <after-bytes> <address> [...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;

public class DumpSorceryPointerWindow extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Expected before, after, addresses");
        }
        int before = Integer.decode(args[0]);
        int after = Integer.decode(args[1]);
        Memory memory = currentProgram.getMemory();
        long imageBase = currentProgram.getImageBase().getOffset();
        for (int index = 2; index < args.length; index++) {
            Address center = toAddr(args[index]);
            println("=== SORCERY_POINTER_WINDOW " + center +
                " IMAGE_BASE=" + currentProgram.getImageBase() + " ===");
            for (int delta = -before; delta <= after; delta += 4) {
                Address at = center.add(delta);
                int raw32 = memory.getInt(at);
                long unsigned32 = Integer.toUnsignedLong(raw32);
                Address rvaAddress = toAddr(imageBase + unsigned32);
                Function rvaFunction = currentProgram.getFunctionManager()
                    .getFunctionContaining(rvaAddress);
                String rvaName = rvaFunction == null ? "-" :
                    rvaFunction.getName() + "@" + rvaFunction.getEntryPoint();
                String absoluteName = "-";
                try {
                    long raw64 = memory.getLong(at);
                    Function absoluteFunction = currentProgram.getFunctionManager()
                        .getFunctionContaining(toAddr(raw64));
                    if (absoluteFunction != null) {
                        absoluteName = absoluteFunction.getName() + "@" +
                            absoluteFunction.getEntryPoint();
                    }
                }
                catch (Exception ignored) {
                    // A 64-bit read can cross an unmapped block at the edge.
                }
                println(String.format(
                    "%s delta=%+d raw32=%08x rva=%s absolute64=%s",
                    at, delta, raw32, rvaName, absoluteName));
            }
        }
    }
}
