// Read-only targeted symbol/xref audit; no project mutations.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.listing.Function;
import java.util.LinkedHashSet;
public class Aa10TradeProtectionAudit extends GhidraScript {
 public void run() throws Exception {
  println("SHA256="+currentProgram.getExecutableSHA256()+" BASE="+currentProgram.getImageBase());
  var fs=new LinkedHashSet<Function>();
  for(String q:getScriptArgs()) if(q.startsWith("@")) {
   var a=toAddr(q.substring(1));var f=getFunctionContaining(a);if(f!=null)fs.add(f);
   for(var r:getReferencesTo(a)){f=getFunctionContaining(r.getFromAddress());println("ADDRESS REF "+r.getFromAddress()+" FN "+(f==null?"none":f.getEntryPoint()));if(f!=null)fs.add(f);}
  }
  var it=currentProgram.getSymbolTable().getAllSymbols(true);
  while(it.hasNext()) {var s=it.next();String n=s.getName(true).toLowerCase(); boolean match=false;
   for(String q:getScriptArgs()) if(n.contains(q.toLowerCase())) match=true;
   if(!match)continue; println("SYMBOL "+s.getAddress()+" "+s.getName(true));
   for(var r:getReferencesTo(s.getAddress())) {var f=getFunctionContaining(r.getFromAddress());println("REF "+r.getFromAddress()+" FN "+(f==null?"none":f.getEntryPoint()));if(f!=null)fs.add(f);}
   if(n.endsWith("::vftable")) for(int k=0;k<3;k++)println("VT "+k+" "+toAddr(getLong(s.getAddress().add(k*8))));
  }
  var d=new DecompInterface();d.openProgram(currentProgram);
  try {for(var f:fs) {println("FUNCTION "+f.getEntryPoint());var r=d.decompileFunction(f,90,monitor);if(r.decompileCompleted())println(r.getDecompiledFunction().getC());}}
  finally {d.dispose();}
 }
}
