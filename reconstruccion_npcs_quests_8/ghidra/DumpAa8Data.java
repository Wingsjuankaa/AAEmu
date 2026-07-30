// Dump bytes, defined data and strings at explicit AA8 addresses.
// Usage: DumpAa8Data.java <output> <length> <address> [address...]
// @category AA8

import java.io.File;
import java.io.PrintWriter;
import java.nio.charset.StandardCharsets;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.DataType;
import ghidra.program.model.listing.Data;
import ghidra.program.model.mem.Memory;

public class DumpAa8Data extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Expected: output file, byte length and at least one address");
        }

        File output = new File(args[0]);
        File parent = output.getParentFile();
        if (parent != null) {
            parent.mkdirs();
        }
        int length = Integer.decode(args[1]);
        Memory memory = currentProgram.getMemory();

        try (PrintWriter out =
                 new PrintWriter(output, StandardCharsets.UTF_8.name())) {
            out.println("PROGRAM " + currentProgram.getName());
            for (int index = 2; index < args.length; index++) {
                Address address = toAddr(args[index]);
                Data data = currentProgram.getListing().getDefinedDataAt(address);
                out.println();
                out.println("===== DATA AT " + address + " =====");
                if (data != null) {
                    DataType type = data.getDataType();
                    out.println("TYPE " + type.getName());
                    out.println("VALUE " + String.valueOf(data.getValue()));
                }
                byte[] bytes = new byte[length];
                int read = memory.getBytes(address, bytes);
                out.print("BYTES ");
                for (int byteIndex = 0; byteIndex < read; byteIndex++) {
                    out.printf("%02x", bytes[byteIndex] & 0xff);
                    if (byteIndex + 1 < read) {
                        out.print(" ");
                    }
                }
                out.println();
                StringBuilder ascii = new StringBuilder();
                for (int byteIndex = 0; byteIndex < read; byteIndex++) {
                    int value = bytes[byteIndex] & 0xff;
                    ascii.append(value >= 0x20 && value <= 0x7e ?
                        (char)value : '.');
                }
                out.println("ASCII " + ascii);
            }
        }

        println("Wrote " + output.getAbsolutePath());
    }
}
