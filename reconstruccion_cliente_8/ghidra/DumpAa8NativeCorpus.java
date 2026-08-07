// Export a deterministic, resumable function corpus from an analyzed AA8 PE.
// Usage:
// DumpAa8NativeCorpus.java <output-dir> <binary-sha256> <architecture>
//   <batch-size> <decompile-timeout-seconds> <anchors-json-or-dash>
// @category AA8

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.block.BasicBlockModel;
import ghidra.program.model.block.CodeBlock;
import ghidra.program.model.block.CodeBlockIterator;
import ghidra.program.model.data.DataType;
import ghidra.program.model.data.DataTypeComponent;
import ghidra.program.model.data.Structure;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.Parameter;
import ghidra.program.model.listing.Variable;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.pcode.HighFunction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class DumpAa8NativeCorpus extends GhidraScript {
    private final Gson gson = new Gson();
    private Address imageBase;
    private Listing listing;
    private ReferenceManager references;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 6) {
            throw new IllegalArgumentException(
                "Expected output-dir, binary-sha256, architecture, batch-size, " +
                "decompile-timeout-seconds and anchors-json-or-dash");
        }
        File outputDirectory = new File(args[0]);
        outputDirectory.mkdirs();
        String binarySha256 = args[1].toUpperCase();
        String architecture = args[2];
        int batchSize = Integer.parseInt(args[3]);
        int timeoutSeconds = Integer.parseInt(args[4]);
        File anchorsFile = "-".equals(args[5]) ? null : new File(args[5]);
        if (batchSize <= 0 || timeoutSeconds <= 0) {
            throw new IllegalArgumentException("Batch size and timeout must be positive");
        }

        imageBase = currentProgram.getImageBase();
        listing = currentProgram.getListing();
        references = currentProgram.getReferenceManager();

        List<Function> allFunctions = new ArrayList<>();
        FunctionIterator iterator = listing.getFunctions(true);
        while (iterator.hasNext()) {
            allFunctions.add(iterator.next());
        }
        allFunctions.sort(
            Comparator.comparingLong(function ->
                function.getEntryPoint().getUnsignedOffset()));

        Set<Long> anchorRvas = loadAnchors(
            anchorsFile, binarySha256, architecture);
        List<Function> selected = new ArrayList<>();
        for (Function function : allFunctions) {
            long rva = rva(function.getEntryPoint());
            if (anchorRvas == null || anchorRvas.contains(rva)) {
                selected.add(function);
            }
        }
        writeMetadata(outputDirectory, binarySha256, architecture);

        DecompInterface decompiler = new DecompInterface();
        decompiler.toggleCCode(true);
        decompiler.toggleSyntaxTree(true);
        decompiler.setSimplificationStyle("decompile");
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException(
                "Decompiler refused program: " + decompiler.getLastMessage());
        }
        try {
            int batchCount = Math.max(1, (selected.size() + batchSize - 1) / batchSize);
            for (int batch = 0; batch < batchCount; batch++) {
                if (monitor.isCancelled()) {
                    break;
                }
                int start = batch * batchSize;
                int end = Math.min(selected.size(), start + batchSize);
                File destination = new File(
                    outputDirectory, String.format("batch-%06d.jsonl", batch));
                if (destination.isFile()) {
                    println("Resume: keeping " + destination.getName());
                    continue;
                }
                File temporary = new File(
                    outputDirectory, "." + destination.getName() + ".partial");
                writeBatch(
                    temporary,
                    selected.subList(start, end),
                    binarySha256,
                    architecture,
                    batch,
                    batchCount,
                    start,
                    selected.size(),
                    allFunctions.size(),
                    timeoutSeconds,
                    decompiler);
                atomicMove(temporary.toPath(), destination.toPath());
                println(
                    "Wrote " + destination.getAbsolutePath() +
                    " (" + (end - start) + " functions)");
            }
        }
        finally {
            decompiler.dispose();
        }
    }

    private Set<Long> loadAnchors(
            File path, String binarySha256, String architecture) throws Exception {
        if (path == null) {
            return null;
        }
        if (!path.isFile()) {
            throw new IllegalArgumentException("Anchor file does not exist: " + path);
        }
        JsonObject root = JsonParser.parseString(
            Files.readString(path.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
        Set<Long> result = new HashSet<>();
        JsonArray anchors = root.getAsJsonArray("anchors");
        for (JsonElement value : anchors) {
            JsonObject anchor = value.getAsJsonObject();
            if (!architecture.equals(anchor.get("architecture").getAsString())) {
                continue;
            }
            String key = anchor.get("binary_key").getAsString().toUpperCase();
            if (!key.endsWith(binarySha256)) {
                continue;
            }
            result.add(anchor.get("entry_rva").getAsLong());
        }
        return result;
    }

    private void writeBatch(
            File output,
            List<Function> functions,
            String binarySha256,
            String architecture,
            int batch,
            int batchCount,
            int startIndex,
            int selectedCount,
            int discoveredCount,
            int timeoutSeconds,
            DecompInterface decompiler) throws Exception {
        try (Writer writer = new OutputStreamWriter(
                 new FileOutputStream(output), StandardCharsets.UTF_8);
             PrintWriter out = new PrintWriter(writer)) {
            Map<String, Object> header = new LinkedHashMap<>();
            header.put("record", "batch");
            header.put("format", "AA8_GHIDRA_NATIVE_CORPUS_V1");
            header.put("program", currentProgram.getName());
            header.put("binary_sha256", binarySha256);
            header.put("architecture", architecture);
            header.put("image_base", imageBase.getUnsignedOffset());
            header.put("batch", batch);
            header.put("batch_count", batchCount);
            header.put("start_index", startIndex);
            header.put("function_count", functions.size());
            header.put("selected_function_count", selectedCount);
            header.put("discovered_function_count", discoveredCount);
            out.println(gson.toJson(header));
            for (Function function : functions) {
                if (monitor.isCancelled()) {
                    throw new InterruptedException("Ghidra monitor cancelled");
                }
                out.println(gson.toJson(
                    functionRecord(function, timeoutSeconds, decompiler)));
            }
            if (out.checkError()) {
                throw new IllegalStateException("Failed writing " + output);
            }
        }
    }

    private Map<String, Object> functionRecord(
            Function function,
            int timeoutSeconds,
            DecompInterface decompiler) throws Exception {
        Map<String, Object> row = new LinkedHashMap<>();
        Address entry = function.getEntryPoint();
        long entryRva = rva(entry);
        byte[] bytes = functionBytes(function);
        row.put("record", "function");
        row.put("entry_va", entry.getUnsignedOffset());
        row.put("entry_rva", entryRva);
        row.put("end_rva", rva(function.getBody().getMaxAddress()) + 1);
        row.put("size", function.getBody().getNumAddresses());
        row.put("byte_sha256", sha256(bytes));
        row.put("mnemonic_sha256", mnemonicSha256(function));
        row.put("name", function.getName());
        row.put("namespace", function.getParentNamespace().getName(true));
        row.put("prototype", function.getPrototypeString(true, true));
        row.put("calling_convention", function.getCallingConventionName());
        row.put("function_kind",
            function.isThunk() ? "thunk" :
            function.isExternal() ? "external" : "function");
        row.put("parameters", parameters(function));
        row.put("locals", locals(function));
        row.put("instructions", instructions(function));
        row.put("basic_blocks", basicBlocks(function));
        row.put("calls", calls(function));
        Map<String, Object> referencesAndStrings = dataReferences(function);
        row.put("data_references", referencesAndStrings.get("references"));
        row.put("strings", referencesAndStrings.get("strings"));

        long started = System.nanoTime();
        DecompileResults result =
            decompiler.decompileFunction(function, timeoutSeconds, monitor);
        row.put("duration_ms", (System.nanoTime() - started) / 1_000_000L);
        if (result.decompileCompleted() &&
            result.getDecompiledFunction() != null) {
            row.put("decompile_status", "confirmed");
            row.put("pseudocode", normalizeNewlines(
                result.getDecompiledFunction().getC()));
            HighFunction high = result.getHighFunction();
            row.put("high_function_present", high != null);
            row.put("error", null);
        }
        else {
            String error = result.getErrorMessage();
            row.put(
                "decompile_status",
                error != null && error.toLowerCase().contains("timeout")
                    ? "timeout" : "failed");
            row.put("pseudocode", null);
            row.put("high_function_present", false);
            row.put("error", normalizeNewlines(error));
        }
        return row;
    }

    private void writeMetadata(
            File outputDirectory,
            String binarySha256,
            String architecture) throws Exception {
        Map<String, Object> root = new LinkedHashMap<>();
        root.put("format", "AA8_GHIDRA_NATIVE_METADATA_V1");
        root.put("program", currentProgram.getName());
        root.put("binary_sha256", binarySha256);
        root.put("architecture", architecture);
        root.put("image_base", imageBase.getUnsignedOffset());

        List<Map<String, Object>> symbols = new ArrayList<>();
        List<Map<String, Object>> vtables = new ArrayList<>();
        SymbolIterator symbolIterator =
            currentProgram.getSymbolTable().getAllSymbols(true);
        while (symbolIterator.hasNext()) {
            Symbol symbol = symbolIterator.next();
            String name = symbol.getName(true);
            String lower = name.toLowerCase();
            boolean isVtable =
                lower.contains("vftable") ||
                lower.contains("vtable") ||
                lower.contains("??_7");
            boolean isRtti =
                lower.contains("rtti") ||
                lower.contains("type descriptor") ||
                lower.contains("complete object locator") ||
                lower.contains("??_r");
            if (!isVtable && !isRtti) {
                continue;
            }
            Address address = symbol.getAddress();
            if (address == null || !currentProgram.getMemory().contains(address)) {
                continue;
            }
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("name", name);
            value.put("rva", rva(address));
            value.put("symbol_type", symbol.getSymbolType().toString());
            value.put("primary", symbol.isPrimary());
            value.put("kind", isVtable ? "vtable" : "rtti");
            symbols.add(value);
            if (isVtable) {
                Map<String, Object> table = new LinkedHashMap<>(value);
                table.put("slots", vtableSlots(address));
                vtables.add(table);
            }
        }
        symbols.sort(Comparator.comparingLong(
            value -> ((Number)value.get("rva")).longValue()));
        vtables.sort(Comparator.comparingLong(
            value -> ((Number)value.get("rva")).longValue()));
        root.put("symbols", symbols);
        root.put("vtables", vtables);

        List<Map<String, Object>> types = new ArrayList<>();
        Iterator<DataType> typeIterator =
            currentProgram.getDataTypeManager().getAllDataTypes();
        while (typeIterator.hasNext()) {
            DataType type = typeIterator.next();
            if (!(type instanceof Structure)) {
                continue;
            }
            Structure structure = (Structure)type;
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("name", structure.getName());
            value.put("category", structure.getCategoryPath().getPath());
            value.put("length", structure.getLength());
            List<Map<String, Object>> fields = new ArrayList<>();
            for (DataTypeComponent component : structure.getDefinedComponents()) {
                Map<String, Object> field = new LinkedHashMap<>();
                field.put("ordinal", component.getOrdinal());
                field.put("offset", component.getOffset());
                field.put("length", component.getLength());
                field.put("name", component.getFieldName());
                field.put(
                    "type", component.getDataType().getDisplayName());
                fields.add(field);
            }
            value.put("fields", fields);
            types.add(value);
        }
        types.sort(
            Comparator.comparing(value ->
                value.get("category") + "/" + value.get("name")));
        root.put("types", types);

        File destination = new File(outputDirectory, "metadata.json");
        File temporary = new File(outputDirectory, ".metadata.json.partial");
        Files.writeString(
            temporary.toPath(),
            gson.toJson(root) + "\n",
            StandardCharsets.UTF_8);
        atomicMove(temporary.toPath(), destination.toPath());
    }

    private List<Map<String, Object>> vtableSlots(Address start) throws Exception {
        List<Map<String, Object>> result = new ArrayList<>();
        Memory memory = currentProgram.getMemory();
        int pointerSize = currentProgram.getDefaultPointerSize();
        int invalid = 0;
        for (int ordinal = 0; ordinal < 512; ordinal++) {
            Address slotAddress = start.add((long)ordinal * pointerSize);
            if (!memory.contains(slotAddress)) {
                break;
            }
            long raw = pointerSize == 8
                ? memory.getLong(slotAddress)
                : Integer.toUnsignedLong(memory.getInt(slotAddress));
            Address target =
                currentProgram.getAddressFactory().getDefaultAddressSpace()
                    .getAddress(raw);
            boolean executable =
                target != null &&
                memory.contains(target) &&
                memory.getBlock(target) != null &&
                memory.getBlock(target).isExecute();
            if (!executable) {
                invalid++;
                if (invalid >= 2) {
                    break;
                }
                continue;
            }
            invalid = 0;
            Function function = listing.getFunctionContaining(target);
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("ordinal", ordinal);
            value.put("slot_rva", rva(slotAddress));
            value.put("target_rva", rva(target));
            value.put("target_name",
                function == null ? null : function.getName());
            result.add(value);
        }
        return result;
    }

    private List<Map<String, Object>> parameters(Function function) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Parameter parameter : function.getParameters()) {
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("ordinal", parameter.getOrdinal());
            value.put("name", parameter.getName());
            value.put("type", parameter.getDataType().getDisplayName());
            value.put("length", parameter.getLength());
            value.put("storage", parameter.getVariableStorage().toString());
            result.add(value);
        }
        return result;
    }

    private List<Map<String, Object>> locals(Function function) {
        List<Map<String, Object>> result = new ArrayList<>();
        for (Variable variable : function.getLocalVariables()) {
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("name", variable.getName());
            value.put("type", variable.getDataType().getDisplayName());
            value.put("length", variable.getLength());
            value.put("storage", variable.getVariableStorage().toString());
            result.add(value);
        }
        return result;
    }

    private List<Map<String, Object>> basicBlocks(Function function) throws Exception {
        List<Map<String, Object>> result = new ArrayList<>();
        BasicBlockModel model = new BasicBlockModel(currentProgram);
        CodeBlockIterator blocks =
            model.getCodeBlocksContaining(function.getBody(), monitor);
        while (blocks.hasNext()) {
            CodeBlock block = blocks.next();
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("start_rva", rva(block.getFirstStartAddress()));
            value.put("end_rva", rva(block.getMaxAddress()) + 1);
            int instructionCount = 0;
            InstructionIterator instructions =
                listing.getInstructions(block, true);
            while (instructions.hasNext()) {
                instructions.next();
                instructionCount++;
            }
            value.put("instruction_count", instructionCount);
            result.add(value);
        }
        result.sort(Comparator.comparingLong(
            value -> ((Number)value.get("start_rva")).longValue()));
        return result;
    }

    private List<Map<String, Object>> instructions(Function function) throws Exception {
        List<Map<String, Object>> result = new ArrayList<>();
        Memory memory = currentProgram.getMemory();
        InstructionIterator iterator =
            listing.getInstructions(function.getBody(), true);
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            byte[] bytes = new byte[instruction.getLength()];
            memory.getBytes(instruction.getAddress(), bytes);
            Map<String, Object> value = new LinkedHashMap<>();
            value.put("rva", rva(instruction.getAddress()));
            value.put("mnemonic", instruction.getMnemonicString());
            value.put("text", instruction.toString());
            value.put("bytes", hex(bytes));
            result.add(value);
        }
        return result;
    }

    private List<Map<String, Object>> calls(Function function) {
        List<Map<String, Object>> result = new ArrayList<>();
        InstructionIterator instructions =
            listing.getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            Reference[] refs = instruction.getReferencesFrom();
            for (Reference reference : refs) {
                if (!reference.getReferenceType().isCall()) {
                    continue;
                }
                Map<String, Object> value = new LinkedHashMap<>();
                value.put("callsite_rva", rva(reference.getFromAddress()));
                value.put("call_kind",
                    reference.getReferenceType().isIndirect()
                        ? "indirect" : "direct");
                Address target = reference.getToAddress();
                if (target != null && currentProgram.getMemory().contains(target)) {
                    value.put("target_rva", rva(target));
                    Function targetFunction = listing.getFunctionContaining(target);
                    value.put("target_name",
                        targetFunction == null ? null : targetFunction.getName());
                    value.put("state",
                        targetFunction == null ? "candidate" : "confirmed");
                }
                else {
                    Symbol symbol = target == null
                        ? null : currentProgram.getSymbolTable().getPrimarySymbol(target);
                    value.put("target_rva", null);
                    value.put("target_name", symbol == null ? null : symbol.getName(true));
                    value.put("state", "corroborated");
                }
                result.add(value);
            }
        }
        result.sort(Comparator.comparingLong(
            value -> ((Number)value.get("callsite_rva")).longValue()));
        return result;
    }

    private Map<String, Object> dataReferences(Function function) {
        List<Map<String, Object>> result = new ArrayList<>();
        List<Map<String, Object>> strings = new ArrayList<>();
        ReferenceIterator iterator =
            references.getReferencesTo(function.getEntryPoint());
        // Force ReferenceManager initialization before walking instructions.
        while (iterator.hasNext()) {
            iterator.next();
        }
        InstructionIterator instructions =
            listing.getInstructions(function.getBody(), true);
        Set<String> seenReferences = new HashSet<>();
        Set<String> seenStrings = new HashSet<>();
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (!reference.getReferenceType().isData()) {
                    continue;
                }
                Address target = reference.getToAddress();
                if (target == null || !currentProgram.getMemory().contains(target)) {
                    continue;
                }
                String referenceIdentity =
                    reference.getFromAddress() + ":" + target;
                if (seenReferences.add(referenceIdentity)) {
                    Map<String, Object> value = new LinkedHashMap<>();
                    value.put("from_rva", rva(reference.getFromAddress()));
                    value.put("to_rva", rva(target));
                    value.put("kind", reference.getReferenceType().getName());
                    result.add(value);
                }
                Data data = listing.getDefinedDataAt(target);
                if (data == null || data.getValue() == null) {
                    continue;
                }
                Object raw = data.getValue();
                String text = raw instanceof String ? (String)raw : null;
                if (text == null || text.isEmpty()) {
                    continue;
                }
                String stringIdentity = target + ":" + text;
                if (seenStrings.add(stringIdentity)) {
                    Map<String, Object> value = new LinkedHashMap<>();
                    value.put("rva", rva(target));
                    value.put("reference_rva", rva(reference.getFromAddress()));
                    value.put("encoding", "ghidra-defined-string");
                    value.put("value", normalizeNewlines(text));
                    strings.add(value);
                }
            }
        }
        result.sort(Comparator.comparingLong(
            value -> ((Number)value.get("from_rva")).longValue()));
        strings.sort(Comparator.comparingLong(
            value -> ((Number)value.get("rva")).longValue()));
        Map<String, Object> combined = new HashMap<>();
        combined.put("references", result);
        combined.put("strings", strings);
        return combined;
    }

    private byte[] functionBytes(Function function) throws Exception {
        ByteArrayOutputStream stream = new ByteArrayOutputStream();
        Memory memory = currentProgram.getMemory();
        InstructionIterator iterator =
            listing.getInstructions(function.getBody(), true);
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            byte[] bytes = new byte[instruction.getLength()];
            memory.getBytes(instruction.getAddress(), bytes);
            stream.write(bytes);
        }
        return stream.toByteArray();
    }

    private String mnemonicSha256(Function function) throws Exception {
        StringBuilder normalized = new StringBuilder();
        InstructionIterator iterator =
            listing.getInstructions(function.getBody(), true);
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            normalized.append(instruction.getMnemonicString().toLowerCase());
            normalized.append('(');
            for (int index = 0; index < instruction.getNumOperands(); index++) {
                if (index > 0) {
                    normalized.append(',');
                }
                normalized.append(instruction.getOperandType(index));
            }
            normalized.append(")\n");
        }
        return sha256(
            normalized.toString().getBytes(StandardCharsets.UTF_8));
    }

    private long rva(Address address) {
        return address.subtract(imageBase);
    }

    private String sha256(byte[] value) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return hex(digest.digest(value));
    }

    private String hex(byte[] value) {
        StringBuilder text = new StringBuilder();
        for (byte item : value) {
            text.append(String.format("%02X", item));
        }
        return text.toString();
    }

    private String normalizeNewlines(String value) {
        return value == null
            ? null : value.replace("\r\n", "\n").replace("\r", "\n");
    }

    private void atomicMove(Path source, Path target) throws Exception {
        try {
            Files.move(
                source,
                target,
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING);
        }
        catch (AtomicMoveNotSupportedException exception) {
            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);
        }
    }
}
