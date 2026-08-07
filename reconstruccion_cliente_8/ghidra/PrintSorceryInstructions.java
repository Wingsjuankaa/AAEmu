// Print instructions around addresses without relying on an older cached class.
// Usage: PrintSorceryInstructions.java <before-count> <after-count> <address> [...]
// @category AA8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class PrintSorceryInstructions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Expected before, after, and addresses");
        }
        int before = Integer.parseInt(args[0]);
        int after = Integer.parseInt(args[1]);
        for (int index = 2; index < args.length; index++) {
            Address address = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(args[index]);
            Instruction current = currentProgram.getListing().getInstructionContaining(address);
            for (int n = 0; n < before && current != null; n++) {
                current = current.getPrevious();
            }
            println("=== SORCERY_INSTRUCTIONS_AROUND " + address + " ===");
            int total = before + after + 1;
            for (int n = 0; n < total && current != null; n++) {
                println(current.getAddress() + " " + current);
                current = current.getNext();
            }
        }
    }
}
