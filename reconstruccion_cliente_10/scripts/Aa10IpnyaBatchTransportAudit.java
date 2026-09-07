// Read-only bounded discovery. Re-anchor exported byte ranges against the active DLL.
// @category AA10
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.listing.Function;
import java.nio.file.*;
import java.util.*;

public class Aa10IpnyaBatchTransportAudit extends GhidraScript {
    public void run() throws Exception {
        Path out=Path.of(getScriptArgs()[0]); Files.createDirectories(out);
        Files.writeString(out.resolve("identity.txt"),"sha256="+currentProgram.getExecutableSHA256()+"\nbase="+currentProgram.getImageBase()+"\nlanguage="+currentProgram.getLanguageID()+"\n");
        Set<String> terms=Set.of("OnChatEntered","OnChatClosed","ExecuteString");
        Set<Function> functions=new LinkedHashSet<>(); StringBuilder refs=new StringBuilder();
        var it=currentProgram.getListing().getDefinedData(true);
        while(getScriptArgs().length == 1 && it.hasNext()) {
            var data=it.next(); Object v=data.getValue();
            if(!(v instanceof String) || !terms.contains((String)v)) continue;
            refs.append(data.getAddress()).append(" ").append(v).append("\n");
            for(var ref:getReferencesTo(data.getAddress())) {
                Function f=getFunctionContaining(ref.getFromAddress());
                refs.append("  ").append(ref.getFromAddress()).append(" ").append(ref.getReferenceType()).append(" function=").append(f==null?"none":f.getEntryPoint()).append("\n");
                if(f!=null) functions.add(f);
            }
        }
        for(int i=1;i<getScriptArgs().length;i++) {
            String arg=getScriptArgs()[i];
            if(arg.startsWith("r:")) {
                var addr=toAddr(arg.substring(2));refs.append("TARGET ").append(addr).append("\n");
                for(var ref:getReferencesTo(addr)) {Function f=getFunctionContaining(ref.getFromAddress());refs.append(ref.getFromAddress()).append(" function=").append(f==null?"none":f.getEntryPoint()).append("\n");if(f!=null)functions.add(f);}
            } else {Function f=getFunctionContaining(toAddr(arg));if(f==null)throw new IllegalStateException("No function "+arg);functions.add(f);}
        }
        Files.writeString(out.resolve("string-refs.txt"),refs);
        DecompInterface dec=new DecompInterface(); dec.openProgram(currentProgram);
        try { for(Function f:functions) {
            var d=dec.decompileFunction(f,30,monitor); String name=f.getEntryPoint().toString();
            if(d.decompileCompleted()) Files.writeString(out.resolve(name+".c"),d.getDecompiledFunction().getC());
            StringBuilder bytes=new StringBuilder();
            for(var range:f.getBody().getAddressRanges()) {
                byte[] b=new byte[(int)range.getLength()];currentProgram.getMemory().getBytes(range.getMinAddress(),b);
                bytes.append(range.getMinAddress().subtract(currentProgram.getImageBase())).append(" ").append(HexFormat.of().formatHex(b)).append("\n");
            }
            Files.writeString(out.resolve(name+".bytes"),bytes);
        }} finally {dec.dispose();}
        println("Ipnya references="+functions.size());
    }
}
