// Read-only: export existing functions referenced by a supplied vtable.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
public class DecompileVtableEntries extends GhidraScript {
 public void run() throws Exception {
  println("SHA256="+currentProgram.getExecutableSHA256()+" BASE="+currentProgram.getImageBase());
  var d=new DecompInterface(); d.openProgram(currentProgram);
  try { for (String arg : getScriptArgs()) {
   var address=toAddr(arg);
   for(int i=0;i<6;i++) {
    var slot=address.add(i*8);
    var f=getFunctionAt(toAddr(getLong(slot)));
    if(f==null)break;
    println("SLOT="+slot+" FUNCTION="+f.getEntryPoint());
    var r=d.decompileFunction(f,45,monitor);
    if(r.decompileCompleted())println(r.getDecompiledFunction().getC());
   }
  }} finally {d.dispose();}
 }
}
