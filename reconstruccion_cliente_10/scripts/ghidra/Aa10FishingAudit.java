// Read-only exact-function export for the r575 fishing/AI investigation.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
public class Aa10FishingAudit extends GhidraScript {
 public void run() throws Exception {
  println("SHA256="+currentProgram.getExecutableSHA256()+" BASE="+currentProgram.getImageBase());
  var d=new DecompInterface(); d.openProgram(currentProgram);
  try { for(String arg:getScriptArgs()) {
   var f=getFunctionContaining(toAddr(arg));
   if(f==null)throw new IllegalArgumentException(arg);
   println("FUNCTION="+f.getEntryPoint());
   var r=d.decompileFunction(f,90,monitor);
   if(!r.decompileCompleted())throw new IllegalStateException(r.getErrorMessage());
   println(r.getDecompiledFunction().getC());
  }} finally { d.dispose(); }
 }
}
